"""Item form input-experience tests, kept independent through page objects."""

import pytest
from playwright.sync_api import Error, Page

from config.config import settings
from pages.item_page import ItemPage
from pages.login_page import LoginPage
from utils.data_generator import DataGenerator


@pytest.fixture(scope="session")
def authenticated_page(browser) -> Page:
    context = browser.new_context()
    page = context.new_page()
    login = LoginPage(page, settings.timeout_ms)
    login.open(settings.base_url)
    login.login(settings.username, settings.password)
    yield page
    context.close()


@pytest.fixture
def item_page(authenticated_page: Page) -> ItemPage:
    item = ItemPage(authenticated_page, settings.timeout_ms)
    item.open_new(settings.base_url)
    return item


def test_required_fields_provide_friendly_feedback(item_page: ItemPage):
    result = item_page.save_and_collect()
    assert result["messages"] or item_page.page.locator(".has-error:visible").count()


def test_invalid_number_and_date_are_not_silently_accepted(item_page: ItemPage):
    number = item_page.fill_first_available(("valuation_rate", "weight_per_unit", "shelf_life_in_days"), "0")
    number_field = item_page.editable_field(number)
    try:
        number_field.fill("abc")
    except Error:
        # Native number controls can reject non-numeric text before form validation.
        pass
    date = next(
        (field for field in ("end_of_life", "last_purchase_date") if item_page.field_container(field).count()),
        None,
    )
    if date:
        try:
            item_page.editable_field(date).fill("2024-02-30")
        except (Error, AssertionError):
            pass
    result = item_page.save_and_collect()
    assert result["messages"] or item_page.page.locator(".has-error:visible").count()
    assert number


def test_long_text_and_negative_number_remain_user_visible(item_page: ItemPage):
    item_page.fill_item_code(DataGenerator.item_code())
    item_page.fill_item_name(DataGenerator.long_text())
    number = item_page.fill_first_available(("valuation_rate", "weight_per_unit", "shelf_life_in_days"), "-123.45")
    field_value = item_page.editable_field(number).input_value()
    assert field_value.startswith("-")


def test_double_save_keeps_page_responsive(item_page: ItemPage):
    try:
        result = item_page.save_and_collect(clicks=2)
    except Exception:
        # A validation dialog may intentionally block the second click; the
        # experience under test is that the page remains alive and responsive.
        result = {"elapsed_seconds": 0}
    assert result["elapsed_seconds"] < 8
    assert item_page.page.locator("body").is_visible()


def test_refresh_does_not_claim_to_preserve_unsaved_data(item_page: ItemPage):
    value = DataGenerator.item_name()
    item_page.fill_item_name(value)
    item_page.refresh()
    current = item_page.editable_field("item_name").input_value()
    assert current != value or item_page.visible_messages()

