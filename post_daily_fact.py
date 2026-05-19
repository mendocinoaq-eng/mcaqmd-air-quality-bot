"""
MCAQMD Daily Air Quality Fact Poster (via Buffer)
Posts a different air quality education fact every day
to the MCAQMD Facebook Page through Buffer's GraphQL API.
Runs via GitHub Actions once daily at 5 PM PT.
"""

import os
import requests
from datetime import datetime
import pytz

# ── Config (set these as GitHub Secrets) ──────────────────────────────────────
BUFFER_API_KEY    = os.environ["BUFFER_API_KEY"]
BUFFER_CHANNEL_ID = os.environ["BUFFER_CHANNEL_ID"]

TIMEZONE       = pytz.timezone("America/Los_Angeles")
BUFFER_API_URL = "https://api.buffer.com"

# ── Daily facts library ────────────────────────────────────────────────────────
FACTS = [
    # General air quality education
    {
        "emoji": "🌬️",
        "fact": "The Air Quality Index (AQI) is a scale from 0 to 500. The higher the number, the more polluted the air and the greater the health concern. An AQI below 50 is considered Good — the best air quality you can have!",
        "hashtags": "#AirQuality #AQI #CleanAir #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🔬",
        "fact": "PM2.5 refers to fine particles 2.5 micrometers or smaller in diameter — about 30 times smaller than a human hair. These tiny particles can travel deep into your lungs and even enter your bloodstream, which is why they are closely monitored.",
        "hashtags": "#PM25 #AirQuality #PublicHealth #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🌿",
        "fact": "Ground-level ozone is not emitted directly into the air — it forms when sunlight reacts with pollution from cars, factories, and other sources. This is why ozone levels are often highest on hot, sunny afternoons.",
        "hashtags": "#Ozone #AirQuality #CleanAir #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🫁",
        "fact": "Children breathe more air relative to their body size than adults, making them more vulnerable to air pollution. On unhealthy air quality days, it is especially important to limit children's outdoor activity.",
        "hashtags": "#AirQuality #ChildHealth #PublicHealth #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🏠",
        "fact": "Indoor air can be 2 to 5 times more polluted than outdoor air. Common indoor pollutants include smoke, cleaning products, pet dander, and mold. Proper ventilation and air filtration can make a big difference.",
        "hashtags": "#IndoorAirQuality #AirQuality #CleanAir #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🚗",
        "fact": "Vehicle emissions are one of the largest sources of air pollution in California. Simple actions like combining errands, carpooling, or choosing cleaner vehicles can significantly reduce your contribution to local air pollution.",
        "hashtags": "#CleanAir #VehicleEmissions #AirQuality #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🌡️",
        "fact": "Hot weather and air pollution are a dangerous combination. High temperatures can worsen ozone levels, and heat stress combined with poor air quality puts extra strain on your heart and lungs. Stay cool and check the AQI on hot days.",
        "hashtags": "#HeatSafety #AirQuality #PublicHealth #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "💨",
        "fact": "Wind plays a major role in air quality. Strong winds can disperse pollutants and improve air quality, but they can also carry wildfire smoke and dust from distant sources into our area.",
        "hashtags": "#AirQuality #WildfireSmoke #CleanAir #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🎭",
        "fact": "Not all masks protect against air pollution. Standard surgical masks and cloth masks do not filter fine particles like PM2.5. An N95 or KN95 respirator, worn correctly, provides meaningful protection during poor air quality events.",
        "hashtags": "#AirQuality #WildfireSmoke #N95 #PublicHealth #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🌲",
        "fact": "Trees and vegetation help improve air quality by absorbing pollutants and producing oxygen. A single mature tree can absorb up to 48 pounds of carbon dioxide per year and filter particulates from the air around it.",
        "hashtags": "#Trees #CleanAir #AirQuality #Environment #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🦋",
        "fact": "In 19th century England, the peppered moth evolved darker coloring because industrial soot had blackened trees and buildings, making light-colored moths easy targets for birds. After the Clean Air Act improved air quality decades later, the moths gradually evolved back to their original light color — one of the most famous examples of evolution driven by air pollution.",
        "hashtags": "#AirQuality #History #CleanAirAct #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🏙️",
        "fact": "The Great Smog of London in December 1952 killed an estimated 12,000 people in just five days. A cold fog mixed with coal smoke and industrial pollution blanketed the city so thickly that people couldn't see their own feet. It is considered the worst air pollution disaster in European history and directly led to the UK's Clean Air Act of 1956.",
        "hashtags": "#AirQualityHistory #GreatSmog #London #CleanAir #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "👁️",
        "fact": "The Ringelmann Scale, developed by French engineer Maximilian Ringelmann in 1888, is one of the oldest tools for measuring air pollution. It consists of a chart with six shades of gray numbered 0 to 5 — from clear to completely black. Smoke inspectors would hold the chart up and compare the shade of smoke coming from a smokestack to determine if it was in violation.",
        "hashtags": "#RingelmannScale #AirQualityHistory #Opacity #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "💨",
        "fact": "Opacity is a measure of how much light smoke or emissions block. Modern air quality regulations use opacity limits to control visible emissions from smokestacks and diesel vehicles. In California, the limit for most sources is 20% opacity — meaning smoke cannot block more than 20% of the light passing through it.",
        "hashtags": "#Opacity #RingelmannScale #AirQuality #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🎓",
        "fact": "Today, certified smoke inspectors use a modernized version of Ringelmann's original method called EPA Method 9 — visually comparing smoke opacity to a standardized scale. Inspectors must pass a rigorous certification test to ensure consistency. MCAQMD staff are trained in this method to evaluate visible emissions from local sources.",
        "hashtags": "#Opacity #RingelmannScale #AirQuality #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "☠️",
        "fact": "In 1948, the industrial town of Donora, Pennsylvania experienced a deadly air pollution event when a temperature inversion trapped toxic emissions from a zinc smelter over the town for five days. Twenty people died and nearly half the town's 14,000 residents became ill. The Donora Disaster is widely credited as the event that sparked the modern air quality movement in the United States.",
        "hashtags": "#AirQualityHistory #Donora #CleanAir #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🚘",
        "fact": "Los Angeles had some of the worst air quality in the world in the 1940s and 50s. Smog was so thick on some days that residents thought the city was under a chemical attack. Scientists eventually discovered that sunlight reacting with vehicle exhaust was the culprit — a new type of pollution that came to be called photochemical smog.",
        "hashtags": "#LosAngeles #SmogHistory #AirQuality #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🌋",
        "fact": "Volcanoes are one of the largest natural sources of air pollution on Earth. A single major eruption can inject millions of tons of sulfur dioxide into the atmosphere, cooling global temperatures and causing acid rain thousands of miles away. The 1783 Laki eruption in Iceland caused crop failures and famine across Europe.",
        "hashtags": "#NaturalAirPollution #Volcanoes #AirQualityHistory #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🕯️",
        "fact": "Before electricity, London's famous 'pea soup' fogs were largely caused by millions of coal fires burning simultaneously for heat and cooking. The fog was so dense and yellow-green from sulfur that it gave rise to the word 'smog' — a combination of 'smoke' and 'fog' — coined around 1905.",
        "hashtags": "#SmogHistory #AirQualityHistory #London #CleanAir #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🏭",
        "fact": "In the early days of industrialization, dark black smoke from a smokestack was seen as a sign of prosperity and hard work — not a problem. Factory owners were proud of their billowing chimneys. It wasn't until the health effects became undeniable that society began to view air pollution as something that needed to be controlled.",
        "hashtags": "#AirQualityHistory #IndustrialRevolution #CleanAir #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🌫️",
        "fact": "The term 'acid rain' was coined in 1852 by Scottish chemist Robert Angus Smith, who noticed that rain near industrial cities was chemically different from rain in rural areas. It took over a century for governments to take meaningful action — the U.S. Clean Air Act Amendments of 1990 finally established a cap-and-trade program that dramatically reduced acid rain.",
        "hashtags": "#AcidRain #AirQualityHistory #CleanAirAct #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🐄",
        "fact": "Livestock are a surprisingly significant source of air pollution. Cattle produce methane — a potent greenhouse gas — during digestion. Globally, livestock account for roughly 14.5% of all human-caused greenhouse gas emissions. This is one reason why agricultural air emissions are regulated and monitored.",
        "hashtags": "#Agriculture #AirQuality #Methane #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🧑‍🚒",
        "fact": "The first person in the U.S. to be convicted of air pollution violations was a Pittsburgh steel mill owner in 1868 — long before federal environmental laws existed. Local ordinances against excessive smoke existed in many American cities as early as the 1880s, driven by complaints from residents tired of soot covering their homes and laundry.",
        "hashtags": "#AirQualityHistory #CleanAir #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🛸",
        "fact": "NASA uses satellites to monitor air quality from space. Instruments like MODIS and TEMPO can detect wildfire smoke, dust storms, and pollution plumes from orbit. This satellite data is increasingly being used alongside ground monitors like MCAQMD's to give a more complete picture of air quality across entire regions.",
        "hashtags": "#NASA #AirQuality #Technology #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🎆",
        "fact": "Fireworks are a surprisingly significant source of air pollution. Studies have shown that PM2.5 levels can spike to Hazardous levels in the hours around Fourth of July celebrations, even in areas with otherwise clean air. The colorful explosions release heavy metals including lead, copper, and barium into the atmosphere.",
        "hashtags": "#Fireworks #AirQuality #PM25 #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🍃",
        "fact": "Leaves are a surprisingly significant source of air pollution when burned. Burning one ton of leaves produces roughly 117 pounds of carbon monoxide and significant amounts of PM2.5 and other pollutants. This is one reason many jurisdictions restrict leaf burning.",
        "hashtags": "#AirQuality #MCAQMD #MendocinoCounty #OpenBurning"
    },
    {
        "emoji": "🌎",
        "fact": "The ozone layer in the upper atmosphere — which protects Earth from harmful ultraviolet radiation — is completely different from the ground-level ozone that is an air pollutant. Upper atmosphere ozone is beneficial and essential to life. Ground-level ozone is harmful and forms from human pollution. Same molecule, very different effects depending on where it is.",
        "hashtags": "#OzoneLayer #AirQuality #Science #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🏔️",
        "fact": "Even remote wilderness areas are not immune to air pollution. Studies have found measurable levels of pesticides, industrial chemicals, and microplastics in the air at the top of the Rocky Mountains and other remote locations — carried there by wind from distant sources thousands of miles away.",
        "hashtags": "#AirQuality #Wilderness #Science #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🚂",
        "fact": "Before diesel trucks dominated freight transport, steam locomotives were a major source of air pollution in the United States. Rail yards in cities were notorious for their thick smoke and soot. The transition from steam to diesel in the 1950s dramatically reduced visible smoke from trains — though diesel brought its own pollution problems.",
        "hashtags": "#AirQualityHistory #Transportation #CleanAir #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🌬️",
        "fact": "Ancient ice cores drilled in Greenland and Antarctica contain tiny air bubbles that preserve samples of Earth's atmosphere going back hundreds of thousands of years. Scientists can read these bubbles like a history book of air quality — and the record clearly shows that pollution levels spiked sharply with the start of the Industrial Revolution.",
        "hashtags": "#AirQualityHistory #ClimateScience #IceCores #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🎻",
        "fact": "The famous Stradivarius violins, made in the late 1600s and early 1700s, are thought to derive part of their unique sound from the wood used to make them — wood that grew during a period called the Little Ice Age when cooler temperatures and lower pollution produced unusually dense tree rings. Air quality and climate have shaped even the world's greatest instruments.",
        "hashtags": "#AirQualityHistory #Science #QuirkyFacts #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🐝",
        "fact": "Air pollution affects pollinators like bees in a surprising way: pollutants chemically alter the scent of flowers, making them harder for bees to find. Research has shown that diesel exhaust can break down the aromatic compounds that bees use to locate food, potentially contributing to pollinator decline.",
        "hashtags": "#Bees #AirQuality #Pollinators #Science #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🏛️",
        "fact": "Air pollution is literally dissolving ancient monuments. The marble of the Parthenon in Athens, the Lincoln Memorial in Washington D.C., and countless other stone structures are being eroded by acid rain and sulfur dioxide at rates far faster than natural weathering. Cleaning up air quality has become an important part of preserving cultural heritage worldwide.",
        "hashtags": "#AirQuality #History #AcidRain #Science #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🧠",
        "fact": "Emerging research suggests that long-term exposure to air pollution may be linked to cognitive decline and an increased risk of dementia. Fine particles and nitrogen dioxide may be able to enter the brain directly through the olfactory nerve. This is one of the most concerning new frontiers in air quality health research.",
        "hashtags": "#BrainHealth #AirQuality #PublicHealth #Science #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🌤️",
        "fact": "One unexpected side effect of the COVID-19 lockdowns in 2020 was a dramatic temporary improvement in air quality around the world. With far fewer vehicles on the road and many factories closed, cities like Los Angeles, New Delhi, and Beijing recorded some of their cleanest air in decades — giving scientists a rare glimpse of what our air could look like with less pollution.",
        "hashtags": "#AirQuality #COVID19 #CleanAir #Science #MCAQMD #MendocinoCounty"
    },
    # Mendocino County / local specific facts
    {
        "emoji": "🏔️",
        "fact": "Mendocino County's mountainous terrain and coastal location create unique air quality conditions. Valley topography can trap pollutants close to the ground on calm, cool nights — a phenomenon called temperature inversion.",
        "hashtags": "#MendocinoCounty #AirQuality #LocalFacts #MCAQMD #Ukiah"
    },
    {
        "emoji": "🔥",
        "fact": "Mendocino County experiences some of the most significant wildfire activity in California. Wildfire smoke can raise PM2.5 levels from Good to Hazardous within hours. Always check the AQI before spending time outdoors during fire season.",
        "hashtags": "#WildfireSmoke #MendocinoCounty #AirQuality #MCAQMD #FireSeason"
    },
    {
        "emoji": "🪵",
        "fact": "Wood burning is one of the largest sources of PM2.5 pollution in Mendocino County during winter months. Burning only dry, seasoned wood — and never burning on No Burn Days — makes a real difference for your neighbors' health.",
        "hashtags": "#WoodBurning #AirQuality #MendocinoCounty #MCAQMD #BurnDay"
    },
    {
        "emoji": "📋",
        "fact": "The Mendocino County Air Quality Management District (MCAQMD) is one of 35 local air districts in California. We are responsible for permitting stationary sources of pollution, enforcing air quality regulations, and monitoring air quality throughout the county.",
        "hashtags": "#MCAQMD #MendocinoCounty #AirQuality #LocalGovernment #Ukiah"
    },
    {
        "emoji": "🌾",
        "fact": "Agricultural burning has historically been used in Mendocino County to manage crop waste. MCAQMD regulates agricultural burning and issues permits to minimize the impact of smoke on local communities.",
        "hashtags": "#AgriculturalBurning #MendocinoCounty #AirQuality #MCAQMD"
    },
    {
        "emoji": "📡",
        "fact": "MCAQMD operates air quality monitoring stations throughout Mendocino County. The data collected feeds directly into the AirNow network, giving residents real-time access to local air quality information at airnow.gov.",
        "hashtags": "#AirMonitoring #MendocinoCounty #MCAQMD #AirQuality #AirNow"
    },
    # Health tips
    {
        "emoji": "❤️",
        "fact": "People with heart disease are at increased risk on poor air quality days. Fine particles can trigger heart attacks, irregular heartbeat, and worsen heart failure. If you have heart disease, check the AQI daily and follow your doctor's guidance on outdoor activity.",
        "hashtags": "#HeartHealth #AirQuality #PublicHealth #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "😮‍💨",
        "fact": "If you have asthma, air quality directly affects your symptoms. High ozone and PM2.5 levels can trigger asthma attacks even in people whose asthma is otherwise well controlled. Always carry your rescue inhaler on days when air quality is poor.",
        "hashtags": "#Asthma #AirQuality #PublicHealth #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "👴",
        "fact": "Adults 65 and older are at higher risk from air pollution because aging naturally reduces the efficiency of the heart and lungs. On Unhealthy or Very Unhealthy air quality days, older adults should stay indoors with windows closed and air filtration running if possible.",
        "hashtags": "#SeniorHealth #AirQuality #PublicHealth #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🤰",
        "fact": "Pregnant women and their unborn babies are vulnerable to air pollution. Exposure to high levels of PM2.5 during pregnancy has been linked to preterm birth and low birth weight. Checking the AQI daily is a simple step to protect you and your baby.",
        "hashtags": "#PregnancyHealth #AirQuality #PublicHealth #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🏃",
        "fact": "When you exercise, you breathe faster and take in more air — which means you also take in more pollutants. On moderate or higher AQI days, consider moving your workout indoors or shifting it to the early morning when air quality tends to be better.",
        "hashtags": "#ExerciseHealth #AirQuality #PublicHealth #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🪟",
        "fact": "On days when outdoor air quality is poor, keeping windows and doors closed and using an air purifier with a HEPA filter can significantly reduce your indoor exposure to harmful particles. Even a box fan with a furnace filter taped to it can help!",
        "hashtags": "#IndoorAirQuality #AirQuality #PublicHealth #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "💧",
        "fact": "Staying hydrated helps your body cope with air pollution. When air quality is poor, your respiratory system works harder to filter out particles. Drinking plenty of water helps keep the mucous membranes in your airways functioning properly.",
        "hashtags": "#HealthTips #AirQuality #PublicHealth #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "📱",
        "fact": "Did you know you can get free air quality alerts sent directly to your phone? Sign up at airnow.gov to receive notifications when air quality in your area reaches levels that may affect your health.",
        "hashtags": "#AirNow #AirQuality #PublicHealth #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🐾",
        "fact": "Air pollution affects pets too! Dogs and cats can experience respiratory irritation on poor air quality days. Limit outdoor time for your pets when AQI is elevated, watch for signs of respiratory distress, and contact your vet if you have concerns.",
        "hashtags": "#PetHealth #AirQuality #MCAQMD #MendocinoCounty"
    },
    # Clean Air Act
    {
        "emoji": "⚖️",
        "fact": "The federal Clean Air Act, first passed in 1963 and significantly strengthened in 1970 and 1990, is the foundation of air quality regulation in the United States. It gives the U.S. EPA authority to set national air quality standards and requires states to develop plans to meet them.",
        "hashtags": "#CleanAirAct #AirQuality #EPA #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🏛️",
        "fact": "Under the Clean Air Act, California has unique authority to set its own, more stringent vehicle emission standards — and other states can choose to adopt California's standards. This has made California a national leader in clean vehicle technology.",
        "hashtags": "#CleanAirAct #California #AirQuality #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "📜",
        "fact": "The 1990 Clean Air Act Amendments created the framework for regulating hazardous air pollutants, acid rain, and ozone-depleting substances. They also established the National Emissions Standards for Hazardous Air Pollutants (NESHAP) program that MCAQMD enforces locally.",
        "hashtags": "#CleanAirAct #NESHAP #AirQuality #MCAQMD #MendocinoCounty"
    },
    # Local air district role in permitting
    {
        "emoji": "📝",
        "fact": "MCAQMD issues permits to businesses and facilities that emit air pollutants — including gas stations, dry cleaners, manufacturers, and agricultural operations. These permits set limits on emissions and require regular inspections to protect local air quality.",
        "hashtags": "#AirPermits #MCAQMD #MendocinoCounty #AirQuality #LocalGovernment"
    },
    {
        "emoji": "🔍",
        "fact": "Before a new business that emits pollutants can open in Mendocino County, it must obtain an Authority to Construct permit from MCAQMD. This ensures that new sources of pollution are evaluated and controlled before they begin operating.",
        "hashtags": "#AirPermits #MCAQMD #MendocinoCounty #AirQuality #Permitting"
    },
    {
        "emoji": "🏭",
        "fact": "MCAQMD conducts regular inspections of permitted facilities to ensure they are operating within their permit conditions. If violations are found, MCAQMD has authority to issue fines and require corrective action to protect public health.",
        "hashtags": "#AirPermits #MCAQMD #MendocinoCounty #AirQuality #Enforcement"
    },
    # FARMER, Carl Moyer, and CAP Incentives
    {
        "emoji": "🚜",
        "fact": "The FARMER Program (Funding Agricultural Replacement Measures for Emission Reductions) is a state-funded grant program that helps farmers replace older, high-polluting agricultural equipment with cleaner alternatives. MCAQMD administers this program locally for Mendocino County farmers.",
        "hashtags": "#FARMER #CleanAir #Agriculture #MCAQMD #MendocinoCounty #Grants"
    },
    {
        "emoji": "💰",
        "fact": "The Carl Moyer Memorial Air Quality Standards Attainment Program provides grants to help businesses, fleets, and individuals replace or repower older, high-emission engines with cleaner technology. MCAQMD administers Carl Moyer funds locally — contact us to find out if you qualify!",
        "hashtags": "#CarlMoyer #CleanAir #Grants #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🌱",
        "fact": "The Community Air Protection (CAP) Incentives program prioritizes funding for cleaner equipment in communities most impacted by air pollution. MCAQMD participates in this program to help bring state incentive funding to Mendocino County residents and businesses.",
        "hashtags": "#CAPIncentives #CleanAir #Grants #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🔧",
        "fact": "Through state incentive programs like Carl Moyer and FARMER, MCAQMD has helped local farmers, truckers, and businesses replace polluting diesel engines with cleaner models — reducing harmful emissions right here in Mendocino County at little or no cost to participants.",
        "hashtags": "#CleanAir #Grants #MCAQMD #MendocinoCounty #CarlMoyer #FARMER"
    },
    # What is an air basin
    {
        "emoji": "🗺️",
        "fact": "An air basin is a geographic region defined by its topography and weather patterns that cause air pollutants to mix together. California is divided into 15 air basins. Mendocino County is part of the North Coast Air Basin, which includes Humboldt, Del Norte, and Trinity counties.",
        "hashtags": "#AirBasin #NorthCoast #MCAQMD #MendocinoCounty #AirQuality"
    },
    {
        "emoji": "🌊",
        "fact": "The North Coast Air Basin, which includes Mendocino County, generally has some of the cleanest air in California due to its coastal location and relatively low population density. However, wildfire smoke and wood burning can significantly impact air quality seasonally.",
        "hashtags": "#NorthCoastAirBasin #AirQuality #MCAQMD #MendocinoCounty #CleanAir"
    },
    # How we measure PM2.5 and PM10
    {
        "emoji": "🔭",
        "fact": "MCAQMD measures PM2.5 using a Beta Attenuation Monitor (BAM 1020) — a highly accurate instrument that draws air through a filter and uses beta radiation to precisely measure the mass of fine particles collected. This data is reported hourly to the AirNow network.",
        "hashtags": "#PM25 #AirMonitoring #BAM1020 #MCAQMD #MendocinoCounty #AirQuality"
    },
    {
        "emoji": "🧪",
        "fact": "PM10 refers to particles 10 micrometers or smaller — larger than PM2.5 but still small enough to be inhaled into the lungs. PM10 includes dust, pollen, and mold spores. MCAQMD monitors PM10 levels to ensure they stay within federal health standards.",
        "hashtags": "#PM10 #AirQuality #AirMonitoring #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "📊",
        "fact": "The BAM 1020 monitor used by MCAQMD works 24 hours a day, 7 days a week, automatically collecting and analyzing air samples every hour. This continuous monitoring gives us real-time data to share with the public and to detect pollution events as they happen.",
        "hashtags": "#AirMonitoring #BAM1020 #MCAQMD #MendocinoCounty #AirQuality"
    },
    # NAAQS
    {
        "emoji": "📏",
        "fact": "The National Ambient Air Quality Standards (NAAQS) are health-based limits set by the U.S. EPA for six major air pollutants: PM2.5, PM10, ozone, carbon monoxide, sulfur dioxide, and nitrogen dioxide. These standards represent the maximum pollution levels considered safe for public health.",
        "hashtags": "#NAAQS #AirQuality #EPA #MCAQMD #MendocinoCounty #PublicHealth"
    },
    {
        "emoji": "✅",
        "fact": "Areas that meet the National Ambient Air Quality Standards (NAAQS) are called 'attainment areas.' Areas that don't meet the standards are called 'nonattainment areas' and must develop plans to reduce pollution. Mendocino County is currently in attainment for all federal standards.",
        "hashtags": "#NAAQS #Attainment #AirQuality #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "🔄",
        "fact": "The EPA periodically reviews and updates the National Ambient Air Quality Standards (NAAQS) as new health science becomes available. In 2024, EPA strengthened the annual PM2.5 standard from 12 to 9 micrograms per cubic meter — reflecting new research on the health effects of fine particle pollution.",
        "hashtags": "#NAAQS #PM25 #AirQuality #EPA #MCAQMD #MendocinoCounty"
    },
    # Naturally occurring asbestos
    {
        "emoji": "⛰️",
        "fact": "Naturally Occurring Asbestos (NOA) is found in certain rock formations throughout California, including parts of Mendocino County. When these rocks are disturbed by grading, construction, or off-road activities, asbestos fibers can be released into the air and inhaled.",
        "hashtags": "#NaturallyOccurringAsbestos #NOA #AirQuality #MCAQMD #MendocinoCounty"
    },
    {
        "emoji": "⚠️",
        "fact": "Exposure to naturally occurring asbestos fibers can cause serious lung diseases including mesothelioma and asbestosis. If you are planning grading or construction in an area with known asbestos-containing rock, contact MCAQMD before you begin work.",
        "hashtags": "#Asbestos #NOA #PublicHealth #MCAQMD #MendocinoCounty #AirQuality"
    },
    {
        "emoji": "🚧",
        "fact": "California law requires that projects disturbing naturally occurring asbestos must take specific dust control measures and notify MCAQMD. MCAQMD can help you determine if your property may be affected and what steps you need to take to protect workers and neighbors.",
        "hashtags": "#Asbestos #NOA #Construction #MCAQMD #MendocinoCounty #AirQuality"
    },
    # NESHAP
    {
        "emoji": "🏗️",
        "fact": "NESHAP stands for National Emission Standards for Hazardous Air Pollutants. These are federal standards set by the EPA to control emissions of toxic air pollutants from specific industrial sources, including asbestos during demolition and renovation projects.",
        "hashtags": "#NESHAP #AirQuality #EPA #MCAQMD #MendocinoCounty #HazardousAir"
    },
    {
        "emoji": "🔑",
        "fact": "MCAQMD is the designated NESHAP enforcement agency for Mendocino County. This means that if you are planning a demolition or renovation project on a building that may contain asbestos, you are required by federal law to notify MCAQMD before work begins.",
        "hashtags": "#NESHAP #Asbestos #MCAQMD #MendocinoCounty #AirQuality #Demolition"
    },
    {
        "emoji": "🏚️",
        "fact": "Under NESHAP regulations, any commerical building being demolished or renovated must be inspected for asbestos-containing materials before work begins. MCAQMD reviews these notifications to ensure asbestos is properly handled and disposed of — protecting workers and the surrounding community.",
        "hashtags": "#NESHAP #Asbestos #MCAQMD #MendocinoCounty #AirQuality #Construction"
    },
    # Smoke Management Plan
    {
        "emoji": "🌫️",
        "fact": "A Smoke Management Plan (SMP) is a plan submitted to MCAQMD by individuals or organizations who want to conduct prescribed burns or agricultural burns. The plan outlines what will be burned, when, and what steps will be taken to minimize smoke impacts on nearby communities.",
        "hashtags": "#SmokeManagement #BurnDay #MCAQMD #MendocinoCounty #AirQuality"
    },
    {
        "emoji": "🗓️",
        "fact": "Prescribed burning is an important land management tool in Mendocino County, used to reduce wildfire fuel loads and restore ecosystems. MCAQMD works with land managers and agencies to approve burns on suitable days when smoke will disperse quickly and not impact communities.",
        "hashtags": "#PrescribedBurn #SmokeManagement #MCAQMD #MendocinoCounty #WildfirePrevention"
    },
    # Burn day status
    {
        "emoji": "🔥",
        "fact": "Each day, MCAQMD determines whether open burning is permitted in Mendocino County based on weather conditions, forecast air quality, and existing smoke levels. A 'Permissive Burn Day' means burning is allowed. A 'No Burn Day' means all open burning is prohibited.",
        "hashtags": "#BurnDay #MCAQMD #MendocinoCounty #AirQuality #OpenBurning"
    },
    {
        "emoji": "🚫",
        "fact": "Burning on a No Burn Day is a violation of MCAQMD regulations and can result in fines. No Burn Days are called to protect public health when weather conditions would trap smoke near the ground. Even a small fire can significantly impact air quality for your entire neighborhood.",
        "hashtags": "#BurnDay #NoBurnDay #MCAQMD #MendocinoCounty #AirQuality"
    },
    # MCAQMD website
    {
        "emoji": "💻",
        "fact": "Did you know MCAQMD has a website with a wide range of resources for residents and businesses? Visit www.mendoair.org to access permit applications, complaint forms, health and safety information, burn day status, smoke management plan submittal, and much more.",
        "hashtags": "#MCAQMD #MendocinoCounty #AirQuality #Website #LocalGovernment"
    },
    {
        "emoji": "📄",
        "fact": "Businesses that need an air quality permit in Mendocino County can find all the necessary forms and applications on the MCAQMD website at co.mendocino.ca.us/aqmd. Our staff is also available to help guide you through the permitting process — call us at (707) 463-4354.",
        "hashtags": "#AirPermits #MCAQMD #MendocinoCounty #AirQuality #Business"
    },
    {
        "emoji": "🌐",
        "fact": "On the MCAQMD website you can find information about our grant programs, submit a smoke management plan, apply for a burn permit, file an air quality complaint, access health and safety resources, and stay up to date on local air quality news. Visit us at www.mendoair.org.",
        "hashtags": "#MCAQMD #MendocinoCounty #AirQuality #Website #CleanAir"
    },
    {
        "emoji": "📣",
        "fact": "If you smell smoke or see a business or neighbor burning illegally, you can file an air quality complaint with MCAQMD via email or phone. Your report helps us protect air quality for the whole community.",
        "hashtags": "#AirQuality #Complaint #MCAQMD #MendocinoCounty #CleanAir"
    },
]

# ── Pick today's fact based on the day of the year ────────────────────────────
def get_todays_fact():
    today = datetime.now(TIMEZONE)
    index = today.timetuple().tm_yday % len(FACTS)
    return FACTS[index]

# ── Build post text ────────────────────────────────────────────────────────────
def build_message():
    fact = get_todays_fact()
    date_str = datetime.now(TIMEZONE).strftime("%A, %B %d, %Y")

    return (
        f"{fact['emoji']} Air Quality Fact of the Day — {date_str}\n\n"
        f"{fact['fact']}\n\n"
        f"📞 Questions? Call us at (707) 463-4354\n"
        f"🌐 www.mendoair.org\n\n"
        f"{fact['hashtags']}"
    )

# ── Post to Buffer via GraphQL API ─────────────────────────────────────────────
def post_to_buffer(message):
    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post {
            id
            text
            status
          }
        }
        ... on NotFoundError      { message }
        ... on UnauthorizedError  { message }
        ... on UnexpectedError    { message }
        ... on RestProxyError     { message }
        ... on LimitReachedError  { message }
        ... on InvalidInputError  { message }
      }
    }
    """
    variables = {
        "input": {
            "text":           message,
            "channelId":      BUFFER_CHANNEL_ID,
            "schedulingType": "automatic",
            "mode":           "shareNow",
            "assets":         [],
            "metadata": {
                "facebook": {
                    "type": "post"
                }
            }
        }
    }
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {BUFFER_API_KEY}",
    }
    resp = requests.post(
        BUFFER_API_URL,
        json={"query": mutation, "variables": variables},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()

    if "errors" in result:
        raise RuntimeError(f"Buffer GraphQL error: {result['errors']}")

    post_result = result["data"]["createPost"]

    if "message" in post_result:
        raise RuntimeError(f"Buffer rejected post: {post_result['message']}")

    return post_result["post"]

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    message = build_message()
    print("\n── Post preview ──────────────────────────────")
    print(message)
    print("──────────────────────────────────────────────\n")

    post = post_to_buffer(message)
    print(f"✅ Posted to Buffer! Post ID: {post['id']} | Status: {post['status']}")

if __name__ == "__main__":
    main()
