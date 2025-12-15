"""Factory for creating Chrome WebDriver instances."""

import os
import shutil
import signal
import socket
import subprocess
import tempfile
from typing import Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from src.config.settings import settings
from src.domain.exceptions import ScrapingError


class DriverFactory:
    """Factory for creating and managing Chrome WebDriver instances."""

    @staticmethod
    def create_driver(proxy: str | None = None) -> tuple[webdriver.Chrome, str, int]:
        """Create a Chrome WebDriver instance.

        Args:
            proxy: Optional proxy URL.

        Returns:
            Tuple of (driver, temp_dir, debug_port).

        Raises:
            ScrapingError: If driver creation fails.
        """
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument(f"--user-agent={settings.chrome_user_agent}")

        # Essential options for servers
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        # Use dynamic port to avoid conflicts
        sock = socket.socket()
        sock.bind(("", 0))
        debug_port = sock.getsockname()[1]
        sock.close()
        options.add_argument(f"--remote-debugging-port={debug_port}")

        # Use unique temporary directory for each instance
        temp_dir = tempfile.mkdtemp()
        options.add_argument(f"--user-data-dir={temp_dir}")

        # Headless mode (configurable desde .env)
        if settings.headless_mode:
            options.add_argument("--headless=new")
        # Si headless_mode es False, el navegador se mostrará (útil para debugging)

        # Configure proxy if available
        if proxy:
            # Extraer IP:PORT del string del proxy
            proxy_server = proxy.replace('http://', '').replace('https://', '').split('@')[-1]
            options.add_argument(f'--proxy-server={proxy_server}')

        service = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            return driver, temp_dir, debug_port
        except Exception as e:
            # Clean up temp directory if driver creation fails
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass
            raise ScrapingError(f"Failed to create Chrome driver: {e}") from e

    @staticmethod
    def cleanup_driver(
        driver: webdriver.Chrome | None,
        service: Service | None,
        temp_dir: str | None,
    ) -> None:
        """Clean up driver resources.

        Args:
            driver: WebDriver instance to close.
            service: Service instance to terminate.
            temp_dir: Temporary directory to remove.
        """
        # Close service first
        if service is not None:
            try:
                if hasattr(service, "process") and service.process:
                    try:
                        service.process.terminate()
                        service.process.wait(timeout=3)
                    except (subprocess.TimeoutExpired, AttributeError):
                        try:
                            service.process.kill()
                        except (AttributeError, ProcessLookupError):
                            pass
            except Exception:
                pass

        # Close driver
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                try:
                    driver.close()
                except Exception:
                    pass

        # Clean up temp directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                DriverFactory._kill_chrome_processes_by_temp_dir(temp_dir)
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    @staticmethod
    def _kill_chrome_processes_by_temp_dir(temp_dir: str) -> None:
        """Kill Chrome processes related to temp directory (Unix/Linux only)."""
        try:
            result = subprocess.run(
                ["pgrep", "-f", f"--user-data-dir={temp_dir}"],
                capture_output=True,
                text=True,
                timeout=2,
            )

            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    try:
                        pid_int = int(pid.strip())
                        os.kill(pid_int, signal.SIGKILL)
                    except (ValueError, ProcessLookupError, PermissionError):
                        pass
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        except Exception:
            pass

