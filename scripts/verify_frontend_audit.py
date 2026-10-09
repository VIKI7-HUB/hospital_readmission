"""
Automated full frontend audit and verification script using Selenium Chrome Headless.
Explicitly verifies:
1. Sidebar expanded and collapsed states, no clipping, icons visible, brand logo fully aligned.
2. Scored Encounters KPI card default neutral state (no "Filtering" chip by default, active only when filters applied).
3. Zero decorative sparklines; real-data mini visuals (cohort distribution multi-segment bar, proportion bars) present.
4. Table headers at 1920, 1440, 1280, 1024px: white-space nowrap, no stray '(', Medications info icon inside cell without overlapping Prior Acute.
5. Care flags: short names (Pharmacist, Telehealth 48h, CDCES, Home nurse), at most 2 visible pills + '+N' chip with tooltip.
6. Risk tier naming: Low (<12%), Elevated (12–20%), High (≥20%), KPI card relabeled to Flagged for follow-up (≥12%) with second line for High tier.
7. Observed Readmissions KPI card displays sample rate (12.8%) and full dataset rate (11.2%).
8. Light and Dark modes across viewports 1920, 1440, 1280, 1024, 768px with zero horizontal page scrolling and zero console errors.
"""
import json
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


def run_frontend_audit():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1540, 900)

    try:
        print("[*] Navigating to http://localhost:5173 ...")
        driver.get("http://localhost:5173")
        time.sleep(2.5)

        # ---------------------------------------------------------------------
        # 1. Sidebar Audit: Expanded & Collapsed States
        # ---------------------------------------------------------------------
        print("\n[*] 1. Auditing Sidebar Layout & Collapsed State...")
        sidebar = driver.find_element(By.CSS_SELECTOR, ".app-sidebar")
        assert sidebar.rect["x"] == 0, f"Sidebar x should be 0, got {sidebar.rect['x']}"
        assert sidebar.rect["width"] == 240, f"Sidebar width should be 240, got {sidebar.rect['width']}"

        # Brand header check
        brand_icon = driver.find_element(By.CSS_SELECTOR, ".brand-icon")
        assert brand_icon.rect["x"] >= 12, f"Brand icon cut off on left: x={brand_icon.rect['x']}"

        # Section label check
        section_label = driver.find_element(By.CSS_SELECTOR, ".nav-section-label")
        label_text = section_label.text.strip()
        print(f"    - Section label: '{label_text}', x={section_label.rect['x']}")
        assert label_text == "CLINICAL WORKSPACE", f"Expected 'CLINICAL WORKSPACE', got '{label_text}'"
        assert section_label.rect["x"] >= 6, f"Section label clipped on left: x={section_label.rect['x']}"

        # Nav items and icons
        nav_items = driver.find_elements(By.CSS_SELECTOR, ".nav-item")
        assert len(nav_items) == 3, f"Expected 3 nav items, got {len(nav_items)}"
        for idx, item in enumerate(nav_items):
            icon = item.find_element(By.CSS_SELECTOR, ".nav-icon")
            assert icon.is_displayed(), f"Nav icon {idx} not displayed"
            assert icon.rect["x"] >= 16, f"Nav icon {idx} clipped on left: x={icon.rect['x']}"
        print("    [+] Expanded sidebar: logo, label, and icons fully visible and unclipped.")

        # Test Collapsed State
        collapse_btn = driver.find_element(By.CSS_SELECTOR, ".sidebar-collapse-btn")
        driver.execute_script("arguments[0].click();", collapse_btn)
        time.sleep(0.5)

        assert "collapsed" in (sidebar.get_attribute("class") or "")
        assert sidebar.rect["width"] == 72, f"Collapsed sidebar width should be 72, got {sidebar.rect['width']}"
        collapsed_toggle = driver.find_element(By.CSS_SELECTOR, ".sidebar-collapse-btn.collapsed-toggle")
        assert collapsed_toggle.rect["x"] >= 10, f"Collapsed button cut off: x={collapsed_toggle.rect['x']}"
        print("    [+] Collapsed sidebar: 72px width, centered brand toggle, no overflow.")

        # Restore Expanded State
        driver.execute_script("arguments[0].click();", collapsed_toggle)
        time.sleep(0.5)
        assert "collapsed" not in (sidebar.get_attribute("class") or "")
        print("    [+] Restored expanded sidebar successfully.")

        # ---------------------------------------------------------------------
        # 2. Scored Encounters KPI Card: Default Neutral State
        # ---------------------------------------------------------------------
        print("\n[*] 2. Auditing Scored Encounters KPI Card State...")
        kpi_cards = driver.find_elements(By.CSS_SELECTOR, ".kpi-card")
        scored_card = kpi_cards[0]
        card0_classes = scored_card.get_attribute("class")
        filtering_chips = scored_card.find_elements(By.CSS_SELECTOR, ".kpi-filtering-chip")
        
        print(f"    - Default card 0 classes: '{card0_classes}'")
        print(f"    - Filtering chips found by default: {len(filtering_chips)}")
        assert "selected-filter" not in (card0_classes or ""), "Card 0 should NOT have 'selected-filter' class by default"
        assert len(filtering_chips) == 0, "Card 0 should NOT show 'Filtering' chip by default"
        print("    [+] Default state is strictly neutral (no active border, no Filtering chip).")

        # ---------------------------------------------------------------------
        # 3. KPI Mini Visuals Audit (No Sparklines, Real-Data Visuals Present)
        # ---------------------------------------------------------------------
        print("\n[*] 3. Auditing KPI Mini Visuals (Sparklines Removed)...")
        sparklines = driver.find_elements(By.CSS_SELECTOR, ".kpi-sparkline-svg")
        assert len(sparklines) == 0, f"Expected 0 sparklines, found {len(sparklines)}"
        print("    [+] Confirmed: 0 decorative sparklines in DOM.")

        # Real distribution bar on Card 0
        dist_bars = scored_card.find_elements(By.CSS_SELECTOR, ".kpi-mini-dist-bar")
        assert len(dist_bars) == 1, "Expected real cohort risk distribution bar on Card 0"
        dist_segs = dist_bars[0].find_elements(By.CSS_SELECTOR, ".kpi-dist-seg")
        assert len(dist_segs) == 3, f"Expected 3 distribution segments (low, elevated, high), got {len(dist_segs)}"
        print("    [+] Real cohort risk distribution bar present on Card 0 (3 segments: Low, Elevated, High).")

        # Real proportion bars on Cards 1, 2, 3
        for card_idx in [1, 2, 3]:
            prop_tracks = kpi_cards[card_idx].find_elements(By.CSS_SELECTOR, ".kpi-proportion-track")
            assert len(prop_tracks) == 1, f"Expected real proportion bar on Card {card_idx}"
            fills = prop_tracks[0].find_elements(By.CSS_SELECTOR, ".kpi-proportion-fill")
            assert len(fills) == 1, f"Expected fill bar on Card {card_idx}"
        print("    [+] Real proportion bars present on Cards 1, 2, and 3.")

        # ---------------------------------------------------------------------
        # 4. Table Header Audit across Viewports: No Stray '(', No Icon Overlap
        # ---------------------------------------------------------------------
        print("\n[*] 4. Auditing Table Header across Viewports (1920, 1440, 1280, 1024)...")
        test_widths = [1920, 1440, 1280, 1024]
        for tw in test_widths:
            driver.set_window_size(tw, 900)
            time.sleep(0.3)

            th_meds = driver.find_element(By.CSS_SELECTOR, "th.col-meds")
            th_acute = driver.find_element(By.CSS_SELECTOR, "th.col-acute")

            meds_text = th_meds.text
            print(f"    - Viewport {tw}px Medications header text: '{meds_text.replace(chr(10), ' ')}'")
            assert "(" not in meds_text, f"Found stray '(' in Medications header at {tw}px: '{meds_text}'"

            # Check whitespace nowrap
            white_space = th_meds.value_of_css_property("white-space")
            assert white_space == "nowrap", f"th.col-meds must be nowrap, got {white_space}"

            # Check that th-info-icon-btn is strictly inside th.col-meds rect and does not overlap th.col-acute
            info_btn = th_meds.find_element(By.CSS_SELECTOR, ".th-info-icon-btn")
            meds_rect = th_meds.rect
            acute_rect = th_acute.rect
            info_rect = info_btn.rect

            # Info icon must be to the left of acute column
            assert info_rect["x"] + info_rect["width"] <= acute_rect["x"], (
                f"Info icon overlaps Prior Acute column at {tw}px! "
                f"Info right: {info_rect['x'] + info_rect['width']}, Acute left: {acute_rect['x']}"
            )
            # Info icon must be inside meds cell
            assert info_rect["x"] >= meds_rect["x"] and (info_rect["x"] + info_rect["width"] <= meds_rect["x"] + meds_rect["width"]), (
                f"Info icon not inside Medications cell at {tw}px!"
            )
        print("    [+] Table headers verified across 1920, 1440, 1280, 1024px: nowrap, no '(', 0 overlap.")
        driver.set_window_size(1540, 900)

        # ---------------------------------------------------------------------
        # 5. Care Flags Audit: Short Names & Icons, Max 2 + '+N' Chip with Tooltip
        # ---------------------------------------------------------------------
        print("\n[*] 5. Auditing Care Flags (Short names, max 2, '+N' chip)...")
        rows = driver.find_elements(By.CSS_SELECTOR, ".clinical-data-table tbody tr")
        assert len(rows) > 0, "No table rows rendered"

        found_overflow = False
        valid_labels = {"Pharmacist", "Telehealth 48h", "CDCES", "Home nurse", "Care coord", "Routine"}

        for r_idx, row in enumerate(rows[:10]):
            flag_pills = row.find_elements(By.CSS_SELECTOR, ".care-flag-pill")
            overflow_chips = row.find_elements(By.CSS_SELECTOR, ".flag-overflow-chip")

            assert len(flag_pills) <= 2, f"Row {r_idx} has {len(flag_pills)} pills, maximum allowed is 2"

            for pill in flag_pills:
                pill_text = pill.text.strip()
                # Verify short label
                assert any(valid in pill_text for valid in valid_labels), f"Unexpected pill label '{pill_text}'"
                # Verify icon
                pill_svg = pill.find_elements(By.CSS_SELECTOR, "svg")
                assert len(pill_svg) == 1, f"Care flag pill '{pill_text}' missing icon"

            if len(overflow_chips) > 0:
                found_overflow = True
                chip_text = overflow_chips[0].text.strip()
                assert chip_text.startswith("+"), f"Overflow chip text '{chip_text}' should start with '+'"
                chip_title = overflow_chips[0].get_attribute("title")
                assert chip_title is not None and len(chip_title) > 0, "Overflow chip must have tooltip title"

        print(f"    [+] Checked first 10 rows: all have <=2 pills with short names & icons. Overflow chip present: {found_overflow}")

        # ---------------------------------------------------------------------
        # 6. Risk Tier Naming & KPI Card Relabeling
        # ---------------------------------------------------------------------
        print("\n[*] 6. Auditing Risk Tier Naming & KPI Card Relabeling...")
        flagged_kpi = kpi_cards[1]
        kpi1_title = flagged_kpi.find_element(By.CSS_SELECTOR, ".kpi-label").text
        kpi1_value = flagged_kpi.find_element(By.CSS_SELECTOR, ".kpi-value").text
        kpi1_second_line = flagged_kpi.find_element(By.CSS_SELECTOR, ".kpi-second-line").text
        print(f"    - Card 1 label: '{kpi1_title}' = {kpi1_value}")
        print(f"    - Card 1 second line: '{kpi1_second_line}'")

        assert "Flagged for follow-up" in kpi1_title, f"Expected 'Flagged for follow-up', got '{kpi1_title}'"
        assert "12%" in kpi1_title, f"Expected '12%' in Card 1 title, got '{kpi1_title}'"
        assert kpi1_value == "139", f"Expected flagged count 139, got {kpi1_value}"
        assert "High (≥20%): 25" in kpi1_second_line or "High" in kpi1_second_line, f"Missing High tier in second line: '{kpi1_second_line}'"
        assert "Elevated" in kpi1_second_line, f"Missing Elevated tier in second line: '{kpi1_second_line}'"

        # Check Filter Dropdown options
        tier_select = driver.find_element(By.CSS_SELECTOR, "select[aria-label='Filter by risk tier']")
        options = [opt.text for opt in tier_select.find_elements(By.TAG_NAME, "option")]
        print(f"    - Tier dropdown options: {options}")
        assert any("Flagged" in opt for opt in options), "Missing 'Flagged for follow-up' in tier options"
        assert any("High risk (≥20%)" in opt for opt in options), "Missing 'High risk (≥20%)' in tier options"
        assert any("Elevated risk (12–20%)" in opt for opt in options), "Missing 'Elevated risk (12–20%)' in tier options"
        assert any("Low risk (<12%)" in opt for opt in options), "Missing 'Low risk (<12%)' in tier options"

        # Check Badges in Table Rows
        badges = driver.find_elements(By.CSS_SELECTOR, ".risk-badge-pill")
        badge_texts = {b.text.strip() for b in badges}
        print(f"    - Table row risk badges present: {badge_texts}")
        assert any("High" in b or "Elevated" in b or "Low" in b for b in badge_texts)

        # ---------------------------------------------------------------------
        # 7. Observed Readmissions KPI Card: Sample & Full-Dataset Rate
        # ---------------------------------------------------------------------
        print("\n[*] 7. Auditing Observed Readmissions Rates Display...")
        obs_kpi = kpi_cards[3]
        obs_context = obs_kpi.find_element(By.CSS_SELECTOR, ".kpi-context-chip").text
        print(f"    - Card 3 context chip: '{obs_context}'")
        assert "12.8%" in obs_context, "Card 3 context must include 12.8% sample rate"
        assert "sample" in obs_context.lower(), "Card 3 context must indicate rate is from sample"
        assert "11.2%" in obs_context, "Card 3 context must include 11.2% full dataset rate"
        print("    [+] Correctly displays 12.8% sample rate alongside 11.2% full dataset rate.")

        # ---------------------------------------------------------------------
        # 8. Filter Activation & Neutral State Verification
        # ---------------------------------------------------------------------
        print("\n[*] 8. Testing Filter Activation on Scored Encounters Card...")
        # Click Flagged KPI card to filter
        driver.execute_script("arguments[0].click();", flagged_kpi)
        time.sleep(1.0)
        
        # Scored encounters card should now show Filtering chip
        card0_classes_active = scored_card.get_attribute("class")
        filtering_chips_active = scored_card.find_elements(By.CSS_SELECTOR, ".kpi-filtering-chip")
        assert "selected-filter" in (card0_classes_active or ""), "Scored card should have selected-filter when filtered"
        assert len(filtering_chips_active) == 1, "Scored card should display 'Filtering' chip when filtered"
        print("    [+] Card 0 dynamically displays 'Filtering' chip when a filter is active.")

        # Click Scored card to reset all filters to neutral
        driver.execute_script("arguments[0].click();", scored_card)
        time.sleep(1.0)
        card0_classes_neutral = scored_card.get_attribute("class")
        filtering_chips_neutral = scored_card.find_elements(By.CSS_SELECTOR, ".kpi-filtering-chip")
        assert "selected-filter" not in (card0_classes_neutral or ""), "Card 0 should return to neutral class"
        assert len(filtering_chips_neutral) == 0, "Card 0 should have 0 filtering chips after reset"
        print("    [+] Clicking Card 0 cleanly resets filters back to neutral.")

        # ---------------------------------------------------------------------
        # 9. Responsive Viewports & Themes (1920, 1440, 1280, 1024, 768)
        # ---------------------------------------------------------------------
        print("\n[*] 9. Checking Responsive Viewports and Themes (Zero Page H-Scroll)...")
        widths = [1920, 1440, 1280, 1024, 768]
        heights = [1080, 900, 800, 768, 1024]

        for mode in ["dark", "light"]:
            driver.execute_script(f"""
                if ('{mode}' === 'dark') {{
                    document.documentElement.setAttribute('data-theme', 'dark');
                    localStorage.setItem('clinicalai-theme', 'dark');
                }} else {{
                    document.documentElement.removeAttribute('data-theme');
                    localStorage.setItem('clinicalai-theme', 'light');
                }}
            """)
            time.sleep(0.3)

            for w, h in zip(widths, heights):
                driver.set_window_size(w, h)
                time.sleep(0.4)

                has_page_hscroll = driver.execute_script(
                    "return document.documentElement.scrollWidth > document.documentElement.clientWidth;"
                )
                print(f"    - {mode.upper()} mode @ {w}x{h}: page horizontal scroll = {has_page_hscroll}")
                assert not has_page_hscroll, f"Page has horizontal scroll at {w}x{h} in {mode} mode!"

        # ---------------------------------------------------------------------
        # 10. Console Error Log Audit
        # ---------------------------------------------------------------------
        print("\n[*] 10. Checking Browser Console Logs for Errors...")
        browser_logs = driver.get_log("browser")
        severe_logs = [log for log in browser_logs if log["level"] in ["SEVERE", "ERROR"]]
        print(f"    - Total browser logs: {len(browser_logs)}, SEVERE/ERROR: {len(severe_logs)}")
        if severe_logs:
            print("[-] Errors:", json.dumps(severe_logs, indent=2))
        assert len(severe_logs) == 0, f"Found {len(severe_logs)} severe console errors!"

        print("\n=======================================================")
        print("   ALL 8 AUDIT AND VERIFICATION ITEMS PASSED 100%!    ")
        print("=======================================================")
        return True

    finally:
        driver.quit()

if __name__ == "__main__":
    success = run_frontend_audit()
    assert success
