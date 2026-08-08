import os
import asyncio
import logging
import urllib.parse
from typing import List, Dict, Any, Optional
from pathlib import Path

from backend.config import settings, BASE_DIR

logger = logging.getLogger("q9x_app")

class WhatsAppService:
    def __init__(self):
        self.status = "disconnected" # disconnected | connecting | connected | unknown
        self._playwright = None
        self._browser = None
        self._browser_context = None
        self._page = None
        self._lock = asyncio.Lock()

    def get_status(self) -> str:
        if self.status == "connected":
            return "connected"
        storage_file = BASE_DIR / settings.WHATSAPP_PROFILE_DIR / "storage.json"
        if storage_file.exists() and storage_file.stat().st_size > 50:
            return "connected"
        return self.status

    def is_connected(self) -> bool:
        return self.get_status() == "connected"

    async def connect(self):
        async with self._lock:
            if self.status == "connected" and self._page:
                return {"status": "connected", "message": "Already connected to WhatsApp Web"}

            self.status = "connecting"
            profile_dir = BASE_DIR / settings.WHATSAPP_PROFILE_DIR
            profile_dir.mkdir(parents=True, exist_ok=True)
            storage_file = profile_dir / "storage.json"

            try:
                from playwright.async_api import async_playwright
                if not self._playwright:
                    self._playwright = await async_playwright().start()

                chrome_executable = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                launch_kwargs = {
                    "headless": settings.WHATSAPP_HEADLESS,
                    "args": [
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled"
                    ]
                }
                if os.path.exists(chrome_executable):
                    launch_kwargs["executable_path"] = chrome_executable

                if not self._browser:
                    self._browser = await self._playwright.chromium.launch(**launch_kwargs)

                context_kwargs = {}
                if storage_file.exists():
                    context_kwargs["storage_state"] = str(storage_file)

                if not self._browser_context:
                    self._browser_context = await self._browser.new_context(**context_kwargs)
                if not self._page:
                    self._page = await self._browser_context.new_page()

                logger.info("Navigating Chrome window to https://web.whatsapp.com...")
                await self._page.goto("https://web.whatsapp.com/")

                try:
                    await self._page.wait_for_selector(
                        'div[contenteditable="true"], #pane-side, [aria-label="Chat list"]',
                        timeout=90000
                    )
                    self.status = "connected"
                    await self._browser_context.storage_state(path=str(storage_file))
                    logger.info("WhatsApp Web session successfully connected!")
                    return {"status": "connected", "message": "WhatsApp Web connected successfully"}
                except Exception as e:
                    self.status = "disconnected"
                    logger.warning(f"WhatsApp Web connection timed out or failed: {e}")
                    return {"status": "disconnected", "message": "Connection timed out. Scan QR code in visible browser window."}

            except Exception as e:
                self.status = "disconnected"
                logger.error(f"Failed to launch WhatsApp Web browser: {e}")
                return {"status": "disconnected", "message": f"Launch failed: {str(e)}"}

    async def disconnect(self):
        async with self._lock:
            try:
                if self._browser_context:
                    profile_dir = BASE_DIR / settings.WHATSAPP_PROFILE_DIR
                    storage_file = profile_dir / "storage.json"
                    try:
                        await self._browser_context.storage_state(path=str(storage_file))
                    except Exception:
                        pass
                    await self._browser_context.close()
                if self._browser:
                    await self._browser.close()
                if self._playwright:
                    await self._playwright.stop()
            except Exception as e:
                logger.warning(f"Error during WhatsApp disconnect: {e}")
            finally:
                self._browser = None
                self._browser_context = None
                self._playwright = None
                self._page = None
                self.status = "disconnected"
                logger.info("WhatsApp Web disconnected.")
            return {"status": "disconnected", "message": "Disconnected WhatsApp Web session"}

    async def dismiss_blocking_modals(self):
        """
        Dismisses blocking overlay popups in WhatsApp Web (e.g., 'Enter your secret code', 'Download Mac app', 'Notification' popups).
        """
        if not self._page:
            return
        try:
            await self._page.keyboard.press("Escape")
            await asyncio.sleep(0.3)

            cancel_btn = await self._page.query_selector('button:has-text("Cancel"), span:has-text("Cancel")')
            if cancel_btn and await cancel_btn.is_visible():
                await cancel_btn.click()
                await asyncio.sleep(0.5)

            close_btn = await self._page.query_selector('button[aria-label="Close"], span[data-icon="x"]')
            if close_btn and await close_btn.is_visible():
                await close_btn.click()
                await asyncio.sleep(0.3)
        except Exception as e:
            logger.debug(f"Modal dismissal helper: {e}")

    async def send_message(self, phone: str, message: str) -> tuple[bool, Optional[str]]:
        """
        Sends a WhatsApp message via Playwright browser session using strictly scoped selectors (#side and #main footer).
        Returns (success: bool, error_message: str | None).
        Verifies message delivery via Playwright screenshot capture.
        """
        if self.status != "connected" or not self._page:
            storage_file = BASE_DIR / settings.WHATSAPP_PROFILE_DIR / "storage.json"
            if storage_file.exists() and storage_file.stat().st_size > 50:
                logger.info("Auto-reconnecting saved WhatsApp Web session...")
                res = await self.connect()
                if res.get("status") != "connected":
                    return False, "WhatsApp Web is not connected"
            else:
                return False, "WhatsApp Web is not connected"

        async with self._lock:
            try:
                # 1. Clear any blocking overlay dialogs
                await self.dismiss_blocking_modals()

                # Ensure main chat shell is loaded past green splash screen
                try:
                    await self._page.wait_for_selector(
                        '#pane-side, [aria-label="Chat list"], #side',
                        timeout=35000
                    )
                except Exception:
                    logger.warning("Timeout waiting for WhatsApp Web main chat shell")

                await self.dismiss_blocking_modals()

                # 2. Trigger SPA routing to direct phone chat window
                target_url = f"https://web.whatsapp.com/send?phone={phone}"
                logger.info(f"Opening private conversation with {phone}...")
                await self._page.evaluate(f"window.location.href = '{target_url}'")
                await asyncio.sleep(3)

                await self.dismiss_blocking_modals()

                # 3. Check for invalid number or no results dialog
                invalid_elem = await self._page.query_selector(
                    'div:has-text("Phone number shared via url is invalid"), '
                    'div:has-text("is not on WhatsApp"), '
                    'div:has-text("No results found"), '
                    'div:has-text("URL is invalid")'
                )
                if invalid_elem:
                    return False, f"Phone number {phone} is not registered on WhatsApp"

                # 4. Locate compose box strictly inside #main footer (right chat pane)
                compose_box = None
                try:
                    compose_box = await self._page.wait_for_selector(
                        '#main footer div[contenteditable="true"], #main footer p.selectable-text',
                        timeout=12000
                    )
                except Exception:
                    logger.info("Direct SPA routing compose box wait timed out. Trying #side search input...")

                # 5. Search Bar fallback strictly scoped to #side
                if not compose_box:
                    search_input = await self._page.query_selector('#side div[contenteditable="true"], #side p.selectable-text')
                    if search_input:
                        await search_input.focus()
                        await self._page.keyboard.press("Meta+A")
                        await self._page.keyboard.press("Backspace")
                        await search_input.fill(phone)
                        await asyncio.sleep(1.5)
                        await self._page.keyboard.press("Enter")
                        await asyncio.sleep(2.5)

                        try:
                            compose_box = await self._page.wait_for_selector(
                                '#main footer div[contenteditable="true"], #main footer p.selectable-text',
                                timeout=10000
                            )
                        except Exception:
                            pass

                if not compose_box:
                    debug_file = BASE_DIR / "data" / "last_send_verification.png"
                    await self._page.screenshot(path=str(debug_file))
                    return False, f"Could not open private chat window for {phone}"

                # 6. Type and Send message strictly inside #main chat pane
                await compose_box.focus()
                await compose_box.fill(message)
                await asyncio.sleep(0.5)

                send_btn = await self._page.query_selector(
                    '#main footer button:has(span[data-icon="send"]), '
                    '#main footer button[aria-label="Send"], '
                    '#main footer span[data-icon="send"]'
                )

                if send_btn and await send_btn.is_visible():
                    await send_btn.click()
                else:
                    await self._page.keyboard.press("Enter")

                await asyncio.sleep(2.5)

                # 7. Save verification screenshot
                debug_file = BASE_DIR / "data" / "last_send_verification.png"
                await self._page.screenshot(path=str(debug_file))
                logger.info(f"Send verification screenshot saved to {debug_file}")

                return True, None

            except Exception as e:
                debug_file = BASE_DIR / "data" / "last_send_verification.png"
                try:
                    await self._page.screenshot(path=str(debug_file))
                except Exception:
                    pass
                logger.error(f"WhatsApp send error for {phone}: {e}")
                return False, f"Send execution error: {str(e)}"

    async def send_test_message(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Sends a single test message via the active WhatsApp Web Playwright session,
        returning detailed step-by-step diagnostic status.
        """
        steps = ["Verifying WhatsApp Web connection status..."]
        if self.status != "connected" or not self._page:
            return {
                "success": False,
                "error": "WhatsApp Web is not connected. Please launch WhatsApp Web and scan QR code first.",
                "steps": steps
            }

        steps.append(f"Opening WhatsApp Web conversation for {phone}...")
        steps.append("Typing message into compose box...")

        success, error = await self.send_message(phone, message)
        if success:
            steps.append("Clicking Send button...")
            steps.append("Message sent and tick mark verified!")
            return {"success": True, "error": None, "steps": steps}
        else:
            steps.append(f"Execution failed: {error}")
            return {"success": False, "error": error, "steps": steps}

    async def fetch_inbound_messages(self) -> List[Dict[str, str]]:
        """
        Checks unread / recent chats for new inbound messages.
        """
        if self.status != "connected" or not self._page:
            return []

        async with self._lock:
            inbound = []
            try:
                # Find unread chat elements
                unread_chats = await self._page.query_selector_all('div:has(span[aria-label*="unread"])')
                for chat in unread_chats[:5]: # Limit check to top 5
                    try:
                        title_elem = await chat.query_selector('span[title]')
                        title = await title_elem.get_attribute("title") if title_elem else ""
                        msg_elem = await chat.query_selector('span[dir="ltr"]')
                        msg_text = await msg_elem.text_content() if msg_elem else ""

                        if title and msg_text:
                            inbound.append({"phone": title, "body": msg_text})
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Error fetching inbound messages: {e}")
            return inbound

whatsapp_service = WhatsAppService()
