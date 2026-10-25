"""Page object for the Frappe/ERPNext login screen."""

from .base_page import BasePage


class LoginPage(BasePage):
    def open(self, base_url: str) -> None:
        self.page.goto(f"{base_url.rstrip('/')}/login", wait_until="domcontentloaded")

    def login(self, username: str, password: str) -> None:
        self.page.locator("input#login_email, input[name='usr'], input[type='email']").first.fill(username)
        self.page.locator("input#login_password, input[name='pwd'], input[type='password']").first.fill(password)
        self.first_visible(
            self.page.locator("button#login_btn:visible"),
            self.page.get_by_role("button", name="Login", exact=True),
            self.page.get_by_role("button", name="登录", exact=True),
        ).click()
        self.page.wait_for_url(lambda url: "/login" not in url, timeout=self.timeout)

