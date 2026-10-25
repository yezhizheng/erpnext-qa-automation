"""Shared, application-agnostic Playwright operations."""

from playwright.sync_api import Locator, Page


class BasePage:
    def __init__(self, page: Page, timeout: int = 15000) -> None:
        self.page = page
        self.timeout = timeout
        self.page.set_default_timeout(timeout)

    def first_visible(self, *locators: Locator) -> Locator:
        for locator in locators:
            for index in range(locator.count()):
                candidate = locator.nth(index)
                if candidate.is_visible():
                    return candidate
        raise AssertionError("No visible matching element was found")

    def field_container(self, fieldname: str) -> Locator:
        return self.page.locator(f"[data-fieldname='{fieldname}']").first

    def editable_field(self, fieldname: str) -> Locator:
        container = self.field_container(fieldname)
        if not container.count():
            raise AssertionError(f"ERPNext field '{fieldname}' does not exist")
        container.evaluate(
            """el => {
                const tab = el.closest('.tab-pane');
                if (tab && !tab.classList.contains('active')) {
                    const link = document.querySelector(`[href="#${tab.id}"], [data-target="#${tab.id}"]`);
                    if (link) link.click();
                }
                const section = el.closest('.form-section');
                const head = section && section.querySelector('.section-head');
                const body = section && section.querySelector('.section-body, .collapse');
                if (head && body && !body.classList.contains('show') && body.offsetParent === null) head.click();
                el.scrollIntoView({block: 'center'});
            }"""
        )
        candidates = container.locator(
            "input:not([type='hidden']), textarea, [contenteditable='true']"
        )
        for index in range(candidates.count()):
            candidate = candidates.nth(index)
            if candidate.is_visible() and candidate.is_editable():
                return candidate
        raise AssertionError(f"ERPNext field '{fieldname}' is not editable")

    def fill_field(self, fieldname: str, value: str) -> None:
        self.editable_field(fieldname).fill(value)

    def visible_messages(self) -> list[str]:
        selectors = ".msgprint:visible, .alert:visible, .frappe-toast:visible, .has-error:visible"
        return [" ".join(text.split()) for text in self.page.locator(selectors).all_inner_texts() if text.strip()]

    def save_button(self) -> Locator:
        return self.first_visible(
            self.page.locator("button.primary-action:visible"),
            self.page.locator(".page-actions button.btn-primary:visible"),
            self.page.get_by_role("button", name="Save", exact=True),
            self.page.get_by_role("button", name="保存", exact=True),
        )

    def click_save(self) -> None:
        self.dismiss_modal()
        self.save_button().click()

    def dismiss_modal(self) -> None:
        modal = self.page.locator(".modal.show:visible")
        if modal.count():
            close = modal.locator("button.btn-modal-close, button:has-text('Close'), button:has-text('关闭')")
            if close.count():
                close.first.click(force=True)
            else:
                primary = modal.locator("button.btn-primary, button[type='submit']")
                if primary.count():
                    primary.first.click(force=True)
                else:
                    self.page.keyboard.press("Escape")

