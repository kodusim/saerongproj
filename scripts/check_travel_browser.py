"""Local browser acceptance checks. Requires playwright and installed Edge.

Run only against the isolated development server; never submits inquiries.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'output/travel-review'
BASE = 'http://127.0.0.1:8012'


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width':1440,'height':1050}, device_scale_factor=1)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE + '/travel', wait_until='networkidle')
        expect(page.locator('.place-row')).to_have_count(24)
        expect(page.locator('.leaflet-container')).to_be_visible()
        page.screenshot(path=str(OUTPUT / 'desktop.png'))
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        with page.expect_response('**/api/travel/places?*'):
            page.select_option('[name=province]', '서울')
        expect(page.locator('.place-meta').first).to_contain_text('서울')
        page.fill('[name=q]', '없는장소xyz')
        page.locator('.search-strip button').click()
        expect(page.locator('#empty-results')).to_be_visible()
        page.locator('[data-reset]').click()
        expect(page.locator('.place-row')).to_have_count(24)
        with page.expect_response('**/api/travel/places?*'):
            page.locator('#next-page').click()
        expect(page.locator('#page-label')).to_contain_text('2 /')
        page.go_back(wait_until='networkidle')
        expect(page.locator('#page-label')).to_contain_text('1 /')
        for i in range(3):
            page.locator('[data-compare]').nth(i).check()
        page.locator('[data-compare]').nth(3).click()
        expect(page.locator('[data-compare]').nth(3)).not_to_be_checked()
        page.locator('#open-compare').click()
        expect(page.locator('#comparison-dialog')).to_be_visible()
        expect(page.locator('.comparison-table thead td')).to_have_count(3)
        page.locator('#comparison-dialog .close-travel-dialog').click()
        for i in range(2):
            page.locator('#place-list [data-save]').nth(i).click()
        expect(page.locator('#saved-count')).to_have_text('2')
        page.locator('[data-detail]').first.click()
        expect(page.locator('#place-dialog .rating-bar')).to_have_count(5)
        page.screenshot(path=str(OUTPUT / 'detail.png'))
        page.locator('#place-dialog .close-travel-dialog').click()
        page.locator('[data-open-notebook]').click()
        expect(page.locator('.notebook-item')).to_have_count(2)
        page.locator('[data-note]').first.fill('방문 전에 운영 시간 확인')
        first = page.locator('.notebook-item h3').first.inner_text()
        page.locator('[data-delta="1"]').first.click()
        expect(page.locator('.notebook-item h3').nth(1)).to_have_text(first)
        with page.expect_download() as download:
            page.locator('#export-notebook').click()
        download.value.save_as(OUTPUT / 'notes.txt')
        assert '방문 전에 운영 시간 확인' in (OUTPUT / 'notes.txt').read_text(encoding='utf-8')
        page.reload(wait_until='networkidle')
        page.locator('[data-open-notebook]').click()
        expect(page.locator('[data-note]').nth(1)).to_have_value('방문 전에 운영 시간 확인')
        page.locator('#notebook-dialog .close-travel-dialog').click()
        with page.expect_download() as download:
            page.locator('#export-results').click()
        download.value.save_as(OUTPUT / 'results.csv')
        assert (OUTPUT / 'results.csv').read_bytes().startswith(b'\xef\xbb\xbf')
        # Recover from a failed search without destroying the current results.
        page.route('**/api/travel/places?*', lambda route: route.fulfill(status=503, body='unavailable'))
        page.select_option('[name=province]', '부산')
        expect(page.locator('#retry-search')).to_be_visible()
        expect(page.locator('.place-row')).to_have_count(24)
        page.unroute('**/api/travel/places?*')
        page.locator('#retry-search').click()
        expect(page.locator('.place-meta').first).to_contain_text('부산')
        page.goto(BASE + '/travel', wait_until='networkidle')
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path=str(OUTPUT / 'mobile.png'))
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('[data-view=map]').click()
        expect(page.locator('#travel-map')).to_be_visible()
        page.locator('#travel-map').scroll_into_view_if_needed()
        page.screenshot(path=str(OUTPUT / 'mobile-map.png'))
        page.locator('#search-map').click()
        expect(page.locator('[data-remove-filter=bounds]')).to_be_visible()
        page.locator('[data-view=list]').click()
        expect(page.locator('#place-list')).to_be_visible()
        page.locator('[data-detail]').first.click()
        expect(page.locator('#place-dialog')).to_be_visible()
        assert page.locator('#place-dialog').evaluate('(el)=>el.scrollWidth <= el.clientWidth + 1')
        page.screenshot(path=str(OUTPUT / 'mobile-detail.png'))
        page.locator('#place-dialog .close-travel-dialog').click()
        for width in (320, 768, 1024, 1440):
            page.set_viewport_size({'width':width,'height':1000})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'travel overflow: {width}'
        page.goto(BASE + '/', wait_until='networkidle')
        expect(page.locator('.home-travel-sample .sample-row')).to_have_count(3)
        page.screenshot(path=str(OUTPUT / 'home-desktop.png'))
        for width in (320, 390, 768):
            page.set_viewport_size({'width':width,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'home overflow: {width}'
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path=str(OUTPUT / 'home-mobile.png'))
        # No-JavaScript users can still search and open actual place details.
        nojs = browser.new_context(java_script_enabled=False)
        static = nojs.new_page()
        static.goto(BASE + '/travel?q=해수욕장')
        expect(static.locator('.place-row').first).to_be_visible()
        static.locator('.place-title').first.click()
        expect(static.locator('.place-full')).to_be_visible()
        nojs.close()
        assert not errors, errors
        browser.close()
    print('Browser checks passed: search, pagination/history, compare, save, notes/reorder/export, CSV, failure recovery, mobile map and detail; no JS errors.')


if __name__ == '__main__':
    main()
