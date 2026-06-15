# Mickey: A Cyberdeck Focus Engine 




### A Short Story
If you forced someone to sit in a chair and stare at a blank wall for 10 hours a day, it would be considered psychological torture. But add a glowing rectangle, and society calls it a "strong work ethic."

I was burning out fast. We’ve spent the last decade creating soulless, corporate, hyper-optimized apps, trading imagination for engagement metrics. Whimsy is what sets us apart from Gen AI, but we forgot that coding used to be an art form. 

I couldn't take my real-life dog, Mickey, to uni with me. So, inspired by the cyberdeck community-a subculture bringing raw creativity and rebellion back to tech-I coded her into a digital hardware watchdog that monitors my RAM, syncs with the weather, and yells at me to take breaks. 

This is Phase 1 of my ultimate Cyberdeck build :DDD.


### What does she actually do?

On the surface, Mickey is a frameless, transparent pixel-art companion that lives on your desktop. But underneath the retro aesthetic, she is a ruthless hardware watchdog and a database-backed burnout enforcer. 

I wanted to build a tool that actually has empathy for the machine *and* the human using it.

* ⚙️ **OS-Level Empathy (`psutil`):** Mickey feels the computer’s pain. A silent background daemon monitors CPU and RAM allocation. If you hoard 50 Chrome tabs while compiling and the CPU spikes over 85%, she panics, enters a "sad" state, and locks the UI to warn you to cool things off.
* 🔒 **Zero Cloud Bloat (`SQLite3`):** No SaaS subscriptions, no data harvesting. Mickey uses a local relational database to permanently and privately track your daily screen time, focus metrics, and UI interactions on your own metal.
* 🌤️ **Async Reality Sync (`threading`):** Background daemons ping satellite weather APIs (`wttr.in`) without blocking the main UI loop. The 2D canvas sky dynamically changes to match the actual weather outside your window. The sun and moon also rise and set based on your local astronomical times.
* 🛑 **The Burnout Enforcer:** A relentless 15-minute timer. After 15 minutes of uninterrupted focus, she locks down. No petting, no playing-just a hard stop until you physically click the `[ BREAK DONE ]` button confirming you stepped away from the keyboard. 
* 😴 **Auto-Sleep:** If it hits 11:00 PM, Mickey automatically goes to sleep and drops a message telling you that you should be resting, too. 


### How to run Mickey

If you want to run Mickey on your own machine, you just need Python and a few basic libraries. 

**1. Clone the repository:**
```bash
git clone [https://github.com/elainaaa-saraaa/mickey-cyberdeck]
cd mickey-cyberdeck
