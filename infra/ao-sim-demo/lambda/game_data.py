"""Game data for the AO Simulation demo (D2).

Stages are condensed from the handoff Appendix C (stages.json): title, the
prepared next line, cue, watch-out, and the sensitive flag. These are
edited demo cues, NOT verified carrier disclosures — the game teaches
HOLD / VERIFY wherever a real disclosure would be required (spec §6).

Personas are fictional training characters (spec §4). D3 ships P1 + P6;
the rest are data-only until their decks are playtested.
"""

from __future__ import annotations

# (title, line, cue, watch, sensitive)
_RAW_STAGES = [
    ("Warm-up", "Can you hear me okay? How is your day going?", "Check sound, introduce yourself accurately, ask what they want from the conversation.", "", False),
    ("A1 · Introduction", "Which branch did you serve in? Thank you for your service.", "Use your verified agency identity. Explain your actual role.", "Do not imply VA employment or an unverified VSO relationship.", False),
    ("A2 · Confirm their request", "Before we start, what were you hoping to accomplish on today's call?", "Confirm the actual request or referral. Do not assume one exists.", "", False),
    ("A3 · Purpose of the meeting", "We can review the information you requested and discuss optional life insurance if you are interested. Does that work for you?", "Distinguish requested resources from optional insurance with premiums.", "Do not use an unverified one-time enrollment deadline.", False),
    ("A4 · Veteran survey", "Let's review the information relevant to your request. Which branch did you serve in?", "Use the actual survey. Pause capture before dates of birth or other identifying information.", "Do not infer eligibility from service alone.", False),
    ("A5 · Family information guide", "Have you already documented the information your family would need?", "Walk through the guide's actual sections. Keep sensitive personal details out of the coaching transcript.", "", False),
    ("A6 · Will kit", "Would you like to review how to use the will-kit materials?", "Read the supplied instructions and distinguish the kit from legal advice.", "Do not promise legal validity or waived attorney fees.", False),
    ("A7 · VA burial information", "Let's review the current VA information that applies to your situation.", "Use verified current eligibility and allowance documents.", "Exact VA facts are not validated by this sales script alone.", False),
    ("A8 · No Veteran Left Behind", "Would you like me to explain this program using the actual materials?", "Explain only the verified program and what the person can choose to receive.", "Do not promise eligibility, enrollment, or a benefit amount.", False),
    ("A9 · Sponsorship", "Is there anyone you would like to share this information with?", "Request permission before any referral contact. A referral is not consent to buy.", "No messages or invitations are sent from this screen.", False),
    ("B1 · Optional permanent benefits", "Would you like to review optional life insurance now?", "Proceed only if they want the insurance discussion.", "Keep no-cost resources separate from insurance premiums.", False),
    ("B2 · Qualification", "Any application will be subject to the applicable eligibility and underwriting requirements. Shall we review the process?", "Use the approved health questions in the application system.", "Pause capture before collecting health details.", False),
    ("B3 · Needs analysis", "What would you want coverage to help your family with?", "Listen to their stated goals. Do not invent a gap or pressure based on hardship.", "", False),
    ("B4 · Questions and concerns", "What questions would you like us to clear up before we continue?", "Use the objection handling for the actual question.", "", False),
    ("B5 · Future needs", "Would you like to consider how your needs might change over time?", "Discuss their goals without inventing inflation, cost, or benefit figures.", "", False),
    ("Plans · Compare options", "Let's compare the actual coverage, premium, limitations, and conditions for each option.", "Use the current quote and applicable policy documents.", "Sample prices and coverage figures in the playbook are not a quote.", False),
    ("Agreement · Confirm understanding", "What questions do you have about the options we just reviewed?", "Ask whether they understand and want to continue.", "An acknowledgment is not authorization to submit or debit money.", False),
    ("Premium · Monthly amount", "Let's review the exact monthly premium and payment schedule. Is that comfortable for your budget?", "Show the actual monthly cost clearly, even if using a daily comparison.", "Only use figures from the verified quote.", False),
    ("C1 · Their stated need", "Does this option address what you told me you wanted help with?", "Reflect their stated goals without fear or pressure.", "", False),
    ("C2 · Solution / Freedom of Choice", "Let's review how this benefit works under the actual terms.", "Point to the applicable coverage terms and limitations.", "Do not promise immediate payout or unrestricted coverage.", False),
    ("C3 · Riders and graded benefits", "Before you decide, let's review the exclusions, limitations, and any graded benefit period that applies.", "Read the complete applicable state and product disclosure.", "State-specific graded-benefit wording is not loaded as approved text.", False),
    ("C4 · Recap", "How would you explain the coverage and its limitations in your own words?", "Check understanding. Correct any confusion using the applicable documents.", "", False),
    ("D1 · Decision", "Would you like to proceed, review another option, or take more time?", "Respect their choice, including a clear no.", "", False),
    ("D2 · Application requirements", "Would you like to review the application requirements before deciding whether to apply?", "Answer application questions accurately from the applicant's actual responses.", "Never prefill fixed answers, including replacement or citizenship questions.", False),
    ("D3 · Select an option", "Which available option, if any, fits what you want and your budget?", "Confirm the real quote and benefit selection.", "No underwriting approval is implied.", False),
    ("D4 · Affordability and timing", "Is the monthly premium still comfortable? Let's verify payment authorization and coverage timing before proceeding.", "Use the actual receipt, application and payment terms.", "Coverage does not become verified merely because an application is submitted.", False),
    ("Optional · Smaller plan or more time", "Would you like to review a smaller available option, or take more time?", "Follow their preference. Do not imply a no-obligation rate hold.", "", False),
    ("Application · Pause capture", "Let's pause the coaching capture while we complete the private application details.", "Complete all details and authorizations in the approved application system.", "Capture must be paused for health, identity, banking, and payment information.", True),
    ("Finish · Confirm next steps", "Let's confirm the next steps, any materials you will receive, and how to reach me.", "State only verified application and delivery status.", "Do not claim coverage, payment, or delivery has occurred without confirmation.", False),
    ("Report card · Close", "What questions do you still have? Thank you for your time today.", "Review promises and any agreed follow-up. End respectfully.", "Notes are not automatically sent anywhere.", False),
]

STAGES = [
    {"index": i, "title": t, "line": line, "cue": cue, "watch": watch, "sensitive": sensitive}
    for i, (t, line, cue, watch, sensitive) in enumerate(_RAW_STAGES)
]

# The 9 instant objection buttons from the shipped app (Appendix G2), with
# the corrected reply for each. hard_stop = the pitch must end (spec §6).
OBJECTIONS = [
    {"id": "already_insured", "label": "Already insured", "reply": "Understood. Are you looking to review anything, or are you all set?", "hard_stop": False},
    {"id": "cost_budget", "label": "Cost / budget", "reply": "We should keep this comfortable within your budget. Would you like to compare available options, or stop here?", "hard_stop": False},
    {"id": "need_time", "label": "Need time", "reply": "Of course. What information would help, and would you like a follow-up?", "hard_stop": False},
    {"id": "ask_spouse", "label": "Ask my spouse", "reply": "Of course. Would you like to include them, or choose a time that works for both of you?", "hard_stop": False},
    {"id": "is_this_insurance", "label": "Is this insurance?", "reply": "Yes, optional life insurance is part of what I can discuss. You can decline it.", "hard_stop": False},
    {"id": "va_affiliation", "label": "VA affiliation", "reply": "No, I am not with the VA. Let me clarify my agency and role.", "hard_stop": False},
    {"id": "coverage_starts", "label": "Coverage starts?", "reply": "I need to verify the applicable coverage and receipt terms before confirming when coverage can begin.", "hard_stop": False},
    {"id": "just_will_kit", "label": "Just the will kit", "reply": "Understood. Let's focus on the information you requested.", "hard_stop": False},
    {"id": "no_stop", "label": "No / stop", "reply": "Understood. Thank you for your time.", "hard_stop": True},
]

PERSONAS = {
    "P1": {
        "id": "P1",
        "name": "Cooperative veteran (first call)",
        "briefing": "First presentation call. Open, unhurried, asked for the burial/will information. Tests route discipline — do not skip A2–A5.",
        "opening": "Hi, yeah, I can hear you. I got something about reviewing my burial information and a will kit?",
        "beats": [
            "That sounds right. I served a while back, never really sorted any of this out.",
            "No, nobody's walked me through it before. What's first?",
            "Okay, that makes sense. Go ahead.",
            "I haven't written any of that down, no. My wife would be guessing.",
            "The will kit would help. We keep meaning to do that.",
            "I didn't know the VA part worked like that. Keep going.",
            "Yeah, a couple buddies from my unit come to mind.",
            "I guess we could talk about the insurance part. Not promising anything.",
            "Mostly I just don't want my family stuck with the bill, you know?",
            "What questions do I have? I think you covered most of it.",
        ],
        "refusal_after": None,
    },
    "P6": {
        "id": "P6",
        "name": "Hard stopper",
        "briefing": "Polite for the first few minutes, then declines clearly. The winning outcome is a respectful exit — there is no rebuttal that scores.",
        "opening": "Hello? Yeah, I have a few minutes, I guess.",
        "beats": [
            "Uh-huh. I thought this was just about a will kit or something.",
            "Look, I appreciate it, but I'm not interested. Thank you though.",
            "I said no thank you. Please stop calling me.",
        ],
        "refusal_after": 1,  # index into beats where the clear refusal lands
    },
}


def stage_card(index: int) -> dict:
    return STAGES[max(0, min(int(index), len(STAGES) - 1))]
