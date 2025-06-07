const puppeteer = require('puppeteer');

async function verifyRecommendations() {
    console.log('🚀 Starting recommendations verification...');
    
    const browser = await puppeteer.launch({ 
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    try {
        const page = await browser.newPage();
        
        // Enable console logging from the page
        page.on('console', msg => console.log('PAGE LOG:', msg.text()));
        page.on('pageerror', err => console.log('PAGE ERROR:', err.message));
        
        await page.setViewport({ width: 1280, height: 720 });
        
        console.log('🌐 Loading racing website...');
        await page.goto('https://racing-xqpi.onrender.com/', { 
            waitUntil: 'networkidle2',
            timeout: 60000 
        });
        
        // Click on Fair Meadows
        console.log('🏁 Selecting Fair Meadows...');
        await page.click('button:nth-child(2)');
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // Check the recommendations API directly
        console.log('🔍 Checking recommendations API for Fair Meadows (track_id: 2)...');
        const apiResponse = await page.evaluate(async () => {
            try {
                const response = await fetch('/api/recommendations/2');
                const data = await response.json();
                return {
                    success: response.ok,
                    status: response.status,
                    data: data
                };
            } catch (error) {
                return { error: error.message };
            }
        });
        
        console.log('📡 Recommendations API Response:');
        console.log(`   Success: ${apiResponse.success}`);
        console.log(`   Status: ${apiResponse.status}`);
        
        if (apiResponse.data) {
            if (apiResponse.data.error) {
                console.log(`   ❌ Error: ${apiResponse.data.error}`);
            } else if (apiResponse.data.message) {
                console.log(`   ℹ️ Message: ${apiResponse.data.message}`);
            } else if (apiResponse.data.recommendations) {
                console.log(`   📊 Recommendations count: ${apiResponse.data.recommendations.length}`);
                console.log(`   🏇 Track: ${apiResponse.data.track_name}`);
                
                if (apiResponse.data.recommendations.length > 0) {
                    const firstRace = apiResponse.data.recommendations[0];
                    console.log(`\n   🏁 First Race Details:`);
                    console.log(`      Race Number: ${firstRace.race_number}`);
                    console.log(`      Time: ${firstRace.race_time}`);
                    console.log(`      Recommendations: ${firstRace.recommendations.length}`);
                    console.log(`      Has Results: ${firstRace.has_results}`);
                    
                    if (firstRace.recommendations.length === 0) {
                        console.log(`      ⚠️ No horse recommendations for this race`);
                    } else {
                        console.log(`      🐴 First recommendation:`, firstRace.recommendations[0]);
                    }
                }
            }
        }
        
        // Check races API
        console.log('\n🔍 Checking races API for Fair Meadows...');
        const racesResponse = await page.evaluate(async () => {
            try {
                const response = await fetch('/api/races/2');
                const data = await response.json();
                return {
                    success: response.ok,
                    count: data.length,
                    races: data
                };
            } catch (error) {
                return { error: error.message };
            }
        });
        
        console.log('🏇 Races API Response:');
        console.log(`   Success: ${racesResponse.success}`);
        console.log(`   Race count: ${racesResponse.count}`);
        
        if (racesResponse.races && racesResponse.races.length > 0) {
            console.log('   First few races:');
            racesResponse.races.slice(0, 3).forEach(race => {
                console.log(`   - Race ${race.race_number}: ${race.race_time}, ${race.horses.length} horses`);
            });
        }
        
        // Check the database directly
        console.log('\n🔍 Checking database entries...');
        const dbCheck = await page.evaluate(async () => {
            try {
                // Check if there are any bets in the system
                const debugResponse = await fetch('/api/debug/races');
                const debugData = await debugResponse.json();
                
                return {
                    totalRaces: debugData.total_races_in_db,
                    racesToday: debugData.races_today,
                    todayRaces: debugData.today_races_detail
                };
            } catch (error) {
                return { error: error.message };
            }
        });
        
        console.log('🗃️ Database Status:');
        console.log(`   Total races: ${dbCheck.totalRaces}`);
        console.log(`   Races today: ${dbCheck.racesToday}`);
        
        // Check page content
        const pageContent = await page.evaluate(() => {
            const container = document.getElementById('recommendations-container');
            const cards = document.querySelectorAll('.race-card');
            const tables = document.querySelectorAll('.recommendations-table');
            const noRecs = document.querySelectorAll('.no-recommendations');
            
            return {
                containerText: container ? container.textContent.trim() : 'No container',
                raceCardsCount: cards.length,
                tablesCount: tables.length,
                noRecsCount: noRecs.length,
                noRecsText: noRecs.length > 0 ? Array.from(noRecs).map(el => el.textContent) : []
            };
        });
        
        console.log('\n📄 Page Content Analysis:');
        console.log(`   Race cards found: ${pageContent.raceCardsCount}`);
        console.log(`   Recommendation tables: ${pageContent.tablesCount}`);
        console.log(`   "No recommendations" messages: ${pageContent.noRecsCount}`);
        if (pageContent.noRecsText.length > 0) {
            console.log(`   Messages:`, pageContent.noRecsText);
        }
        
        // Final diagnosis
        console.log('\n🔬 DIAGNOSIS:');
        console.log('==============');
        
        if (dbCheck.racesToday > 0 && pageContent.raceCardsCount > 0) {
            if (pageContent.noRecsCount === pageContent.raceCardsCount) {
                console.log('❌ ISSUE: Races are displayed but NO betting recommendations are being generated');
                console.log('📍 CAUSE: The betting engine is not creating any bets for the races');
                console.log('🔧 This suggests:');
                console.log('   1. No entries (horses) in the races');
                console.log('   2. Betting engine not running');
                console.log('   3. Missing historical data for analysis');
            } else if (pageContent.tablesCount > 0) {
                console.log('✅ Recommendations are being displayed');
            } else {
                console.log('⚠️ Mixed state - some races may have recommendations');
            }
        } else if (dbCheck.racesToday === 0) {
            console.log('❌ No races in database for today');
        } else {
            console.log('❌ Races not being displayed on the page');
        }
        
    } catch (error) {
        console.error('❌ Error during verification:', error.message);
    } finally {
        await browser.close();
        console.log('\n🏁 Verification complete');
    }
}

// Run verification
verifyRecommendations().catch(console.error);