from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
from datetime import datetime, timedelta
from selenium.webdriver.common.keys import Keys


# Configuration
LOGIN_URL = "https://institutvajrayogini.seminardesk.com/Account/Login"
USERNAME = "lauren@institutvajrayogini.fr"
PASSWORD = "taralauren888"

def setup_driver():
    options = Options()
    options.add_argument("--window-size=1200,800")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = {
                runtime: {},
            };
        '''
    })
    
    return driver

def handle_cookies(driver):
    try:
        for selector in [
            "#cookie-accept", 
            "#CybotCookiebotDialogBodyButtonAccept",
            ".cookie-consent-accept",
            "button.cookie-btn"
        ]:
            try:
                btn = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                btn.click()
                print("✓ Cookie consent accepted")
                time.sleep(1)
                return True
            except:
                continue
    except Exception as e:
        print(f"Cookie handling: {str(e)}")
    return False

def login(driver):
    print("Navigating to login page...")
    driver.get("https://institutvajrayogini.seminardesk.com/Account/Login")
    time.sleep(3)

    handle_cookies(driver)

    try:
        print("Waiting for username field...")
        username = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "UserName_I"))
        )
        print("✓ Found username field")
        driver.execute_script("arguments[0].scrollIntoView(true);", username)
        time.sleep(1)

        username.clear()
        username.send_keys(USERNAME)
        print("✓ Username entered")

        password = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.ID, "Password_I"))
        )
        password.clear()
        password.send_keys(PASSWORD)
        print("✓ Password entered")

        login_btn = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.ID, "Button_CD"))
        )
        login_btn.click()
        print("✓ Login button clicked")

        WebDriverWait(driver, 5).until(
            lambda d: "Account/Login" not in d.current_url
        )
        print("✓ Login successful!")
        return True

    except Exception as e:
        print("⚠️ Login input failed:", e)
        driver.save_screenshot("login_failure.png")
        print("Screenshot saved as login_failure.png")
        print(driver.page_source[:5000])
        input("Try manual login if needed. Press Enter to continue...")
        return "Account/Login" not in driver.current_url

def go_to_reports(driver):
    print("Navigating to reports page...")
    driver.get("https://institutvajrayogini.seminardesk.com/Buchungen/Berichte")
    time.sleep(3)

    # Date values
    yesterday = (datetime.today() - timedelta(days=1)).strftime("%d/%m/%Y")
    six_months_later = (datetime.today() + timedelta(days=180)).strftime("%d/%m/%Y")
    print(f"Using date range: {yesterday} to {six_months_later}")

    try:
        from_date = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "FromDate_I"))
        )
        from_date.clear()
        from_date.send_keys(yesterday)
        print("✓ From date entered")

        till_date = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "TillDate_I"))
        )
        till_date.clear()
        till_date.send_keys(six_months_later)
        print("✓ Till date entered")

    except Exception as e:
        print(f"⚠️ Failed to enter dates: {e}")
        driver.save_screenshot("date_entry_failure.png")


def select_report_and_load(driver):
    try:
        print("Selecting report type...")

        report_dropdown = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "ReportSelection_I"))
        )

        report_dropdown.click()
        report_dropdown.send_keys("Rapport cuisine")
        time.sleep(1)
        report_dropdown.send_keys(Keys.ARROW_DOWN)
        report_dropdown.send_keys(Keys.ENTER)
        print("✓ Report dropdown selection confirmed via keyboard")

        time.sleep(1)  # Let the form update before clicking
        load_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "ActionLoad_I"))
        )
        driver.execute_script("arguments[0].click();", load_button)
        print("✓ Load button clicked via JavaScript")

    except Exception as e:
        print(f"⚠️ Failed to select report and load: {e}")
        driver.save_screenshot("report_select_failure.png")


def export_csv(driver, from_date_obj, to_date_obj):
    # Reformat dates for URL (m/d/yyyy)
    from_url_date = from_date_obj.strftime("%-m/%-d/%Y")
    to_url_date   = to_date_obj.strftime("%-m/%-d/%Y")

    report_url = (
        "https://institutvajrayogini.seminardesk.com/"
        f"Buchungen/Reports/0/Rapport%20cuisine?"
        f"FromDate={from_url_date}&TillDate={to_url_date}"
    )
    print(f"Navigating to report: {report_url}")
    driver.get(report_url)
    time.sleep(3)

    try:
        # 1) click the “Export” arrow (uses the dxviewerExport binding)
        export_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "div[data-bind^='dxviewerExport']")
            )
        )
        export_btn.click()
        print("✓ Export dropdown opened")

        # 2) wait for the CSV entry to be visible in the overlay…
        csv_div = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "div[role='menuitem'][aria-label='CSV']")
            )
        )

        # 3) click it via JS (helps avoid “element intercept” issues)
        driver.execute_script("arguments[0].click()", csv_div)
        print("✓ CSV export triggered")

        # 4) give the download a moment
        time.sleep(5)

    except Exception as e:
        print(f"⚠️ Failed to export CSV: {e}")
        driver.save_screenshot("csv_export_failure.png")


def main():
    driver = setup_driver()
    try:
        if login(driver):
            print("\n🎉 SUCCESS! You're now logged in.")

            from_date = datetime.today() - timedelta(days=1)
            to_date = datetime.today() + timedelta(days=180)

            export_csv(driver, from_date, to_date)

            input("Press Enter to close browser when done...")
        else:
            print("\n🚫 Login failed after all attempts.")
    finally:
        driver.quit()
        print("Browser closed.")


if __name__ == "__main__":
    main()
