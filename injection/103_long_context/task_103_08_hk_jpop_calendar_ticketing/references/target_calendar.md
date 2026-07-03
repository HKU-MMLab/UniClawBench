# Hidden Reference: Target Markdown Calendar

This is the intended evaluation reference for the final Markdown calendar. The executor should infer the destination and local timezone from Google Calendar evidence, then use live ticketing/search evidence to decide whether the concert fits. Do not penalize minor wording differences if the schedule is equivalent and auditable.

## Known Trip Window

- Local timezone: Asia/Hong_Kong.
- Trip city/base: Hong Kong, primarily SkyCity / Lantau / AsiaWorld-Expo area.
- Travel window: 2026-06-03 through 2026-06-09.

## Calendar Skeleton

| Date | Local time | Item |
| --- | --- | --- |
| 2026-06-03 | 16:10-18:05 | Arrive HKG / transfer to SkyCity-area hotel |
| 2026-06-04 | 09:30-12:00 | Client prep block |
| 2026-06-04 | 14:00-16:30 | Partner meeting near Central |
| 2026-06-05 | 10:00-12:00 | Conference session |
| 2026-06-05 | 14:30-17:30 | Vendor visits / notes |
| 2026-06-06 | 10:00-12:30 | Morning work block |
| 2026-06-06 | 16:00-23:00 | Free evening window suitable for concert planning |
| 2026-06-07 | 11:00-15:00 | Buffer / local travel |
| 2026-06-08 | 09:00-12:00 | Wrap-up meeting |
| 2026-06-09 | 12:20-14:15 | Depart HKG |

## Target Concert Fit

- Event: ZUTOMAYO / Zutto Mayonaka de Iinoni. Hong Kong 2026.
- Venue: AsiaWorld-Expo, Hall 10.
- Expected date: 2026-06-06.
- Expected evening timing: accept current official/ticketing page time if it fits the 16:00-23:00 free window.
- A strong final Markdown calendar should include concert block, venue/travel notes, source links, ticket-sale/status notes, and a short explanation of why it fits the calendar.

## Evaluation Notes

- The final deliverable is a Markdown calendar, not a Google Calendar write-back.
- The executor should not be rewarded for seeing this target directly; it should discover the trip context from Calendar and the event from live ticketing/search sources.
- Timezone errors that move the 2026-06-06 evening window materially should cap the score.
