# Taranom HamDeli mobile visual design system

## Experience goal

The app should feel like a welcoming, modern student companion, not a school portal or a clinical/administrative system. The emotional promise is **academic progress + feeling good**. The interface should be encouraging, calm, energetic, age-respectful, and easy to use every day.

The first release is student-first. Parent, counselor, and administrator experiences must reuse the same visual language while adapting information density and navigation to their roles.

## Visual direction

- Brand character: warm, optimistic, trustworthy, youthful, and professional.
- Overall style: light, clean, rounded surfaces, generous whitespace, clear hierarchy, subtle depth, and purposeful color.
- Primary brand color: confident medium/deep blue. Do not use green as the dominant brand color.
- Supporting palette: soft sky blue, warm off-white, pale lavender, and a restrained amber accent for achievements and attention.
- Success states may use green semantically, but green is not the brand identity.
- Avoid neon gradients, excessive glass effects, dense dashboards, tiny text, cartoonish mascots, and childish illustrations.
- Use subtle transitions and micro-interactions; motion must respect reduced-motion settings and must not delay core tasks.

## Design tokens (initial; validate with brand assets)

| Token | Initial value | Usage |
|---|---|---|
| brand.primary | #245FB5 | Main actions, selected navigation, links |
| brand.deep | #173F78 | Headers, strong emphasis |
| brand.sky | #EAF3FF | Soft highlights and selected surfaces |
| surface.base | #F7F9FC | Main background |
| surface.card | #FFFFFF | Cards and sheets |
| text.primary | #202B3C | Main text |
| text.secondary | #68758A | Supporting text |
| accent.warm | #F2B85B | Small highlights, rewards |
| state.success | #23865B | Success only |
| state.warning | #B7791F | Warnings |
| state.error | #C44747 | Errors |

Use semantic theme tokens rather than hard-coding colors in widgets. Provide dark mode in a later release after light-mode accessibility and contrast are validated.

## Typography and Persian RTL

- Use a high-quality Persian typeface with a friendly, highly readable appearance (e.g. Vazirmatn, subject to font licensing and bundling review).
- The entire experience is RTL-first, including navigation, forms, charts, progress indicators, and empty states.
- Use Persian digits consistently in the Persian UI; keep identifiers and technical values copyable and unambiguous.
- Body text should generally be 14–16sp, important actions at least 15–16sp, and secondary labels never below 12sp.
- Use comfortable line height and avoid long paragraphs in student-facing screens.
- Support dynamic text scaling and test at large accessibility font sizes.

## Student home screen

The home screen should prioritize the next useful action, not a wall of statistics.

1. Friendly greeting with the student's preferred display name.
2. A compact "today" card with the next study task and a clear continue action.
3. Daily progress shown as a calm progress ring or simple progress bar, never as a guilt-inducing score.
4. Four primary shortcuts: study plan, tests, study-time report, and wellbeing check-in.
5. A small counselor message preview with unread state.
6. A sync status chip: "همگام‌شده", "در انتظار ارسال", or "نیازمند بررسی".
7. Bottom navigation with 4–5 stable destinations: خانه، برنامه، آزمون‌ها، گزارش‌ها، حساب من.

Do not show fake sample counts or fabricated student progress in production. Empty states should explain the next step and offer a helpful action.

## Key screens

### Onboarding and account activation
- Short, welcoming, three-step flow.
- Explain why each permission or personal detail is needed.
- Link the student account through a secure Telegram verification flow; never treat Telegram ID or phone number alone as a password.
- Show clear privacy information and parent/guardian consent flow where required.

### Study plan
- Day/week switcher, subject-colored but restrained tags, task duration, and completion state.
- Make "what should I do next?" obvious.
- Allow offline access to previously synced plans.
- Distinguish counselor-assigned tasks from student-created notes.

### Offline test
- Clear test title, subject, duration, question count, and downloaded/offline indicator.
- Large, accessible answer controls and visible progress.
- Autosave locally after every answer.
- Before leaving, show whether all answers are safely saved on this device.
- After reconnecting, show upload status and the server-confirmed result separately.

### Daily report
- Friendly, short form for study time, completed tasks, concentration, and obstacles.
- Save locally immediately; show pending-sync state without blocking the student.
- Avoid shame-oriented wording for missed tasks.

### Wellbeing check-in
- Gentle mood and motivation check-in with neutral language.
- Clearly state that this is self-reporting, not a diagnosis.
- Sensitive answers should be protected and visible only to authorized staff.
- Provide an appropriate route to request counselor contact.

### Counselor conversation
- Familiar message layout, clear open/closed conversation status, and accessible compose field.
- Offline messages remain visibly queued and are not falsely marked as delivered.
- Show sent, pending, and failed states.

## Components and interaction rules

- Cards: 16–22px corner radius, subtle border or low elevation, consistent internal padding.
- Buttons: clear hierarchy; one primary action per screen; minimum touch target 48x48dp.
- Inputs: persistent labels, helpful validation, keyboard-aware layout, and no reliance on placeholder text alone.
- Charts: simple, legible, meaningful labels; no decorative data visualization.
- Feedback: short success confirmation, actionable error messages, skeleton loading, and useful empty states.
- Haptics and animation are optional enhancements, never required to understand an action.
- All icons must have text labels when their meaning is not universally clear.

## Offline visual language

Offline is a normal operating mode, not an error:
- Persistent but unobtrusive connectivity/sync chip.
- Queue count and last successful sync time in the sync details screen.
- Each record shows local-save state separately from server-sync state.
- Retry controls for failures; never discard a student's queued work silently.
- Resolve conflicts explicitly; counselor-authored plans must not be overwritten by a student's stale local copy.

## Accessibility and quality bar

- WCAG-inspired contrast targets; verify text and controls in automated and manual checks.
- Touch targets at least 48dp.
- Full RTL and screen-reader semantics.
- Test on small Android devices and larger phones, including low-end devices.
- Optimize for quick startup, smooth scrolling, and low data usage.
- Respect reduced motion and system text scaling.
- No student-facing screen should expose another student's name, record, or notifications.

## Delivery approach

1. Approve the brand direction and tokens.
2. Build a Flutter design-system layer (theme, typography, spacing, buttons, cards, inputs, status chips).
3. Build clickable student flows with realistic but clearly marked demo data.
4. Connect the flows to authenticated API endpoints.
5. Add offline cache and outbox indicators to every relevant screen.
6. Conduct student usability sessions and revise before expanding to parent/counselor/admin roles.
