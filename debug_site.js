const puppeteer = require('puppeteer');

async function checkOurSite() {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    try {
        const page = await browser.newPage();
        
        // Check the main page
        console.log('Checking main page...');
        await page.goto('https://racing-xqpi.onrender.com/', { waitUntil: 'networkidle2' });
        
        const pageTitle = await page.title();
        console.log('Page title:', pageTitle);
        
        // Check if Fair Meadows shows up in tracks
        console.log('\nChecking /api/tracks...');
        const tracksResponse = await page.goto('https://racing-xqpi.onrender.com/api/tracks');
        const tracksData = await tracksResponse.json();
        console.log('Tracks:', tracksData);
        
        // Find Fair Meadows track ID
        const fairMeadows = tracksData.find(track => track.name === 'Fair Meadows');
        if (!fairMeadows) {
            console.log('ERROR: Fair Meadows track not found!');
            return;
        }
        
        console.log('Fair Meadows track ID:', fairMeadows.id);
        
        // Check recommendations for Fair Meadows
        console.log('\nChecking /api/recommendations/2...');
        const recResponse = await page.goto(`https://racing-xqpi.onrender.com/api/recommendations/${fairMeadows.id}`);
        const recData = await recResponse.json();
        console.log('Recommendations response:', JSON.stringify(recData, null, 2));
        
        if (Array.isArray(recData) && recData.length === 0) {
            console.log('\n❌ PROBLEM: Site shows no races for Fair Meadows today');
            console.log('But user reports 8 live races at the track!');
        } else {
            console.log('\n✅ Site shows races:', recData.length);
        }
        
        // Check if we can trigger sync
        console.log('\nTesting sync endpoint...');
        try {
            const syncResponse = await fetch('https://racing-xqpi.onrender.com/api/sync/force-fair-meadows', {
                method: 'POST'
            });
            const syncResult = await syncResponse.json();
            console.log('Sync result:', syncResult);
        } catch (e) {
            console.log('Sync error:', e.message);
        }
        
    } catch (error) {
        console.error('Error:', error);
    } finally {
        await browser.close();
    }
}

checkOurSite();