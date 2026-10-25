"""Page object for creating and exercising an ERPNext Item form."""

from time import monotonic

from .base_page import BasePage


class ItemPage(BasePage):
    path = "/app/item/new-item"

    def open_new(self, base_url: str) -> None:
        self.page.goto(f"{base_url.rstrip('/')}{self.path}", wait_until="domcontentloaded")
        self.page.locator("[data-fieldname='item_code'], [data-fieldname='item_name']").first.wait_for(
            state="visible", timeout=self.timeout
        )

    def fill_item_code(self, value: str) -> None:
        self.fill_field("item_code", value)

    def fill_item_name(self, value: str) -> None:
        self.fill_field("item_name", value)

    def fill_first_available(self, fieldnames: tuple[str, ...], value: str) -> str:
        for fieldname in fieldnames:
            if self.field_container(fieldname).count():
                self.fill_field(fieldname, value)
                return fieldname
        raise AssertionError(f"None of the fields are available: {fieldnames}")

    def save_and_collect(self, clicks: int = 1) -> dict:
        started = monotonic()
        for _ in range(clicks):
            try:
                self.click_save()
            except Exception:
                if _ == 0:
                    raise
        self.page.wait_for_timeout(500)
        return {"elapsed_seconds": monotonic() - started, "messages": self.visible_messages()}

    def refresh(self) -> None:
        self.page.reload(wait_until="domcontentloaded")
        self.page.locator("[data-fieldname='item_code'], [data-fieldname='item_name'], .form-page").first.wait_for(
            state="visible", timeout=self.timeout
        )

