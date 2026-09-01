<!-- SYNTHETIC DOCUMENT — fictional demo content, not a real operating procedure. -->
<!-- version: 1.0 -->

# Ticket Quality (SYNTHETIC)

## 2.1 What makes a ticket usable

A usable escalation ticket lets the duty manager act without re-contacting
the reporter. It states what happened, how bad it is, what is being asked
for, and what evidence supports that request. Vague summaries such as
"network issue, please check" are not acceptable.

## 2.2 Never invent missing fields

If a required field — cause, customer count, duration, or region — is not
available in the source data, the ticket must show that field as unknown or
omit it with an explicit note, never fill it with a plausible-sounding
guess. A ticket author who is uncertain about a value should leave it
unknown rather than approximate it.

## 2.3 Draft status and human review

Every generated ticket starts in DRAFT status. A draft is not sent anywhere
and has no operational effect. A ticket only becomes actionable after a
human reviewer explicitly confirms it; automated systems, including any
assistant that helped compose the draft, may not confirm a ticket on a
human's behalf.
