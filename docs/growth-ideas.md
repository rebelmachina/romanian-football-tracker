# @renasterea.nationalei: growth ideas

**Goal:** keep people who follow Romanian football informed and hyped up, and get kids to look up at these players and think *"one day I want to play for Romania."*

**What we already have to build on** (as of 30 Oct 2026):
- 78 Romanians tracked at clubs in 34 countries; 7 of them are 20 or younger.
- Since 1 August: 62 club goals and 57 assists, across 104 matches with a goal or an assist.
- For each of those 104 matches we know the **minute** of the goal or assist. 46 of them already have a **highlights video link** found by the scraper.
- Daily story and feed post images, posted automatically after your approval in GitHub.
- Ratings, positions, club crests, U21 and senior national-team standings, and the FIFA ranking.

Effort: 🟢 small · 🟡 medium · 🔴 large. ⚙️ = can be automated with what we already have.

---

## 1. Goal and assist video clips (top priority)

Short clips are what spreads on Instagram: Reels get shown to people who don't follow you yet, while photos mostly reach people who already do.

### Copyright is the catch
Match footage belongs to the leagues and broadcasters. Re-uploading it gets posts taken down. After a few takedowns the account loses reach, and in the end it can be **deleted**, which would be a sad end for an account that's meant to be deleted only when Romania wins the World Cup. So here are the routes, from safest to riskiest:

| Route | How | Risk | Effort |
|---|---|---|---|
| **A. Share official clips to our story** | Most clubs post their goals as Reels within hours. Share them to our story with "Share to story", tag the player and add our caption. The video stays theirs, with credit and a link back. | None | 🟢 about 2 minutes a day by hand (the API can't share other people's posts) |
| **B. Collab posts with clubs** | Ask clubs to add @renasterea.nationalei as a *collaborator* on their goal Reel, or invite them to ours. The Reel then appears on both profiles. Start with clubs that have several Romanians, e.g. Turkish and Hungarian clubs. | None | 🟡 a DM per club, then a habit |
| **C. Ask for permission** | DM clubs and leagues: "Romanian fan page, we post our players' goals with credit; may we repost?" Smaller leagues (Cyprus, Lithuania, Slovakia, Israel, Thailand) often say yes. Keep a list of who agreed. | Low, once agreed | 🟡 |
| **D. Our own animated goal Reels** ⚙️ | No footage at all: a 6–10 second animation of the story card with the score popping up, the scorer's name, the minute ("⚽ 67'") and the club crest, plus a "watch the goal ↗" link in the caption. We own it 100%. | None | 🟡 one-time build: render HTML to MP4 with Playwright video recording; then automatic |
| **E. Reupload clips cut from broadcasts** | Cut 10–20 seconds from the highlights video at the known minute and post them as Reels. | **High**: takedowns and account strikes | 🔴 not recommended without permission |

**Recommendation:** start A tomorrow (manual, free and safe), build D next (automated and always ours), and run B and C in the background. When a club says yes, those clips move up to proper Reels.

**Tooling note:** we already know each goal's minute and often the highlights link. If a club or league gives permission, we could later automate "cut the 15 seconds around minute X" for those sources only.

---

## 2. Content that makes kids dream

1. **"La vârsta ta" (At your age)** 🟡⚙️: one card per player showing where they were at 12, 15 and 17 (youth club, first senior game, first match abroad) next to where they are now. Ends with "Tu unde vei fi?" ("Where will you be?"). It's the post most likely to make a kid stop scrolling and think "that could be me."
2. **"Drumul spre tricolor" (The road to the national team)** 🟡: a weekly carousel per player: hometown → first club → move abroad → national-team debut. Slide 1 is a photo-free title card in our style. Hometowns spread across Romania mean kids from Bistrița, Buzău or Craiova see someone from *their* town.
3. **Next generation spotlight** 🟢⚙️: a monthly post about the 7 players aged 20 or under, plus the U21 group standings we already scrape. "The future is already playing abroad."
4. **Map: "Românii în lume"** 🟢⚙️: a world map with every country where a Romanian plays (34 now), updated monthly. It looks great as a feed post and gets shared and saved.
5. **First goal abroad, first match in Europe** ⚙️: special celebration cards when a young player gets their first goal for a club abroad. We can detect it automatically from match history.
6. **Comment-reply challenge** 🟢: "Ce număr vei purta la națională?" ("What number will you wear for Romania?") or "Care e idolul tău?" ("Who's your idol?"). Easy comments help reach, and kids love answering.

> Kids and safety: don't repost photos or videos of children, and don't ask kids to send them in. Keep it to text replies, polls and quizzes. If we ever run a "send your goal" campaign, it has to be through a parent, with written consent.

---

## 3. Hype: stay "the account to check"

1. **Team of the week** 🟡⚙️: every Monday, a lineup graphic of the best Romanian performers abroad, picked by rating and filled position by position (we have both). Very shareable, and gets people arguing in the comments.
2. **Monthly leaderboards** 🟢⚙️: top scorers, top assisters and most minutes among Romanians abroad. Carousel: one slide per leaderboard.
3. **Weekend preview** 🟡⚙️: every Friday, "Weekend Romanians play this weekend" with kick-off times in Romanian time. It needs upcoming fixtures, and the scraper can probably get them from the same source.
4. **National-team matchday kit** 🟡: a countdown story the day before, a lineup card, and a result card with ratings after the final whistle. Our biggest days will be national-team windows.
5. **Milestones and streaks** ⚙️: "3 games in a row with a goal", "100th match in Europe", "10 goals this season". Detected automatically from the data.
6. **Birthday cards** 🟢⚙️: "La mulți ani, Ianis!" These reliably get likes, and players and families often repost them. Needs birth dates; we already have ages, so this is a small scraper addition.
7. **"Golul săptămânii" (Goal of the week) vote** 🟢: a Sunday story poll between 2–4 goals of the week (the clips shared under 1A), with the winner posted Monday. Polls can only be added in the app, so this is a manual step.

---

## 4. Growth mechanics

1. **Tag players and clubs** ⚙️ 🟢: the API supports tagging people in images. Keep a list of player and club Instagram handles, and tag them on every post. Players see the tag and many of them repost, which is the fastest free growth we can get. **Highest return of anything in this list.**
2. **Collab posts** ⚙️: Instagram's API also supports inviting collaborators on feed posts. Invite the player's club on the daily post.
3. **Posting times**: test 08:00 (catches overnight results, people on the commute) against 19:00–21:00 Romanian time. The current workflow posts whenever you approve, so we could hold approved posts until a set time.
4. **Story highlights on the profile** 🟢: "Goluri" (goals), "Naționala" (national team), "Tineri" (youngsters), "Echipa săptămânii" (team of the week), with covers in our navy and gold. Makes the profile look like a proper destination.
5. **Link in bio** 🟢: the tracker site, where every player, match and highlight is one tap away.
6. **Same assets on TikTok and YouTube Shorts** 🟡: the animated Reels from 1D work unchanged there. TikTok is where most kids are.
7. **Reply to every comment** 🟢 in the first month. Early on, that's what builds a community.
8. **Fan-page network** 🟡: friendly shout-out swaps with other Romanian football accounts (club fan pages, Liga 1 accounts). Not competitors: we cover the Romanians *abroad*.

---

## 5. Measure what works

- `ig_automation.py insights` and `report` already exist (in `renasterea_nationalei/scripts`). Run them weekly, and use the report's "style notes" to adjust captions.
- Watch **shares and saves** more than likes. They're the signals Instagram uses to show posts to new people.
- Simple targets for the first 3 months:

| Metric | Month 1 | Month 3 |
|---|---|---|
| Followers | 100 | 1,000 |
| Posts per week | 7 daily + 1 special | 7 daily + 3 specials + Reels |
| Avg reach per post | 2× followers | 3× followers |

---

## Suggested order

1. **This week:**
   - 1A: share club clips to stories.
   - 4.1: player and club handles plus auto-tagging.
   - 4.4 and 4.5: story highlights and link in bio.
2. **Next 2 weeks:**
   - 1D: animated goal Reels.
   - 3.1: team of the week.
   - 2.4: world map.
3. **This month:**
   - 2.1 "La vârsta ta" and 2.2 "Drumul spre tricolor".
   - 3.2: monthly leaderboards.
   - 1B/1C: club outreach.
4. **Later:**
   - 3.3: weekend preview.
   - 3.6: birthday cards.
   - 4.6: TikTok and Shorts.
   - 3.5: milestones.
