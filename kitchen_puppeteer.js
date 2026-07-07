/**
 * Alternative: Node.js with Puppeteer (JavaScript version)
 * 
 * Install: npm install puppeteer
 * Run: node kitchen_puppeteer.js
 * 
 * Puppeteer is fast, reliable, and great for automation.
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// Configuration
const LOGIN_URL = 'https://institutvajrayogini.seminardesk.com/Account/Login';
const PDF_URL = 'https://institutvajrayogini.seminardesk.com/Buchungen/Berichte';
const USERNAME = 'lauren@institutvajrayogini.fr';
const PASSWORD = 'your_password';
const DOWNLOAD_DIR = path.join(__dirname, 'downloads');

// Ensure download directory exists
if (!fs.existsSync(DOWNLOAD_DIR)) {
    fs.mkdirSync(DOWNLOAD_DIR, { recursive: true });
}

async function loginAndDownloadPDF() {
    const browser = await puppeteer.launch({
        headless: false, // Set to true for automation
    });
    
    const page = await browser.newPage();
    
    // Set download path
    const client = await page.target().createCDPSession();
    await client.send('Page.setDownloadBehavior', {
        behavior: 'allow',
        downloadPath: DOWNLOAD_DIR
    });
    
    try {
        // Step 1: Login
        console.log('Navigating to login page...');
        await page.goto(LOGIN_URL, { waitUntil: 'networkidle0' });
        
        console.log('Entering credentials...');
        await page.waitForSelector('input#txtUser', { timeout: 10000 });
        await page.type('input#txtUser', USERNAME);
        await page.type('input#txtPass', PASSWORD);
        await page.click('input#btnLogin');
        
        // Wait for login to complete
        console.log('Waiting for login to complete...');
        await page.waitForNavigation({ waitUntil: 'networkidle0' });
        console.log('✓ Login successful');
        
        // Step 2: Navigate to PDF page
        console.log(`\nNavigating to PDF URL: ${PDF_URL}`);
        await page.goto(PDF_URL, { waitUntil: 'networkidle0' });
        
        // Step 3: Trigger PDF download
        // Adjust this based on how the PDF is accessed on your site
        console.log('Waiting for page to load...');
        
        // Option A: If there's a download link/button
        // await page.click('selector_for_download_button');
        
        // Option B: If you need to interact first (e.g., set date)
        // const today = new Date().toLocaleDateString('en-US');
        // await page.type('input#FromDate_I', today);
        // await page.click('button_to_generate_pdf');
        
        // Option C: If PDF is directly accessible, you can download it directly:
        // const pdfBuffer = await page.pdf({ format: 'A4' });
        // const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        // fs.writeFileSync(
        //     path.join(DOWNLOAD_DIR, `kitchen_report_${timestamp}.pdf`),
        //     pdfBuffer
        // );
        
        // Wait a bit for download to complete
        await page.waitForTimeout(3000);
        
        console.log('✓ PDF download initiated');
        console.log(`Check ${DOWNLOAD_DIR} for the downloaded file`);
        
    } catch (error) {
        console.error(`\nAn error occurred: ${error.message}`);
        await page.screenshot({ path: path.join(DOWNLOAD_DIR, 'error_screenshot.png') });
        throw error;
    } finally {
        await browser.close();
    }
}

// Run the script
loginAndDownloadPDF()
    .then(() => console.log('\nScript completed successfully'))
    .catch(error => {
        console.error('Script failed:', error);
        process.exit(1);
    });






