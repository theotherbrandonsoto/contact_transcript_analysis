"""
generate_tickets.py

Generates a realistic synthetic support ticket CSV for the transcript-analysis project.
Customer IDs, plan types, and churn status are seeded from the same distribution
as the metrics-store project so both repos feel like one coherent system.

Output: data/support_tickets.csv
"""

import csv
import random
import uuid
from datetime import datetime, timedelta

random.seed(42)

# --- Configuration ---
NUM_CUSTOMERS = 200
TICKETS_PER_CUSTOMER_RANGE = (1, 5)
OUTPUT_PATH = "data/support_tickets.csv"

# Plan types matching metrics-store distribution
PLAN_TYPES = ["Basic", "Standard", "Premium"]
PLAN_WEIGHTS = [0.4, 0.35, 0.25]

# Taxonomy: Primary -> Secondary -> [Tertiary options]
TAXONOMY = {
    "Billing": {
        "Duplicate Charge": ["Subscription Upgrade Flow", "Payment Method Update", "Promo Code Applied"],
        "Failed Payment": ["Credit Card Expired", "Insufficient Funds", "Bank Decline"],
        "Refund Request": ["Cancellation Refund", "Overcharge Refund", "Trial Extension"],
        "Invoice Question": ["Monthly Summary", "Annual Billing", "Tax Documentation"],
    },
    "Online Ordering": {
        "Page Not Loading": ["Checkout Flow", "Menu Display", "Mobile Browser"],
        "Menu Not Updating": ["Item Availability", "Price Sync", "Category Order"],
        "Order Not Received": ["Third-Party Integration", "Notification Failure", "POS Sync"],
        "Ordering Disabled": ["Account Suspension", "Setup Incomplete", "Integration Error"],
    },
    "Marketing / SEO": {
        "Google Listing Issue": ["GMB Sync", "Address Incorrect", "Hours Not Updating"],
        "Website Not Updating": ["Content Change", "Image Upload", "Domain Issue"],
        "SEO Performance": ["Ranking Drop", "Review Response", "Keyword Targeting"],
        "Campaign Not Running": ["Email Campaign", "SMS Campaign", "Ad Integration"],
    },
    "Product / Feature": {
        "Feature Not Working": ["Dashboard", "Notifications", "Reporting"],
        "Feature Request": ["Custom Branding", "Multi-Location", "API Access"],
        "Performance Issue": ["Slow Load Time", "Timeout Error", "Data Lag"],
        "Integration Issue": ["POS Integration", "Payment Gateway", "Third-Party App"],
    },
    "Account Access": {
        "Login Issue": ["SSO Failure", "Password Reset", "2FA Problem"],
        "Permissions Error": ["Staff Access", "Admin Role", "Read-Only Mode"],
        "Account Locked": ["Too Many Attempts", "Suspicious Activity", "Billing Hold"],
        "Account Setup": ["New User Invite", "Profile Incomplete", "Timezone Setting"],
    },
    "Onboarding": {
        "Setup Confusion": ["POS Connection", "Domain Setup", "Menu Import"],
        "Integration Help": ["Square Integration", "Toast Integration", "Clover Integration"],
        "Training Request": ["Dashboard Walkthrough", "Reporting Tutorial", "Campaign Setup"],
        "Go-Live Issue": ["Site Not Published", "Ordering Not Active", "Listing Not Live"],
    },
}

# Ticket body templates per primary category
TICKET_TEMPLATES = {
    "Billing": [
        "I was charged twice this month and need a refund right away.",
        "My payment failed again even though I updated my card.",
        "Can you send me an invoice for my records? I can't find it in the portal.",
        "I signed up for the annual plan but I'm still being billed monthly.",
        "There's an unexpected charge on my account from last week.",
    ],
    "Online Ordering": [
        "My online ordering page is completely broken, customers can't place orders.",
        "I updated my menu yesterday but the changes aren't showing up on my site.",
        "A customer said they placed an order but I never received it in my POS.",
        "The checkout page keeps throwing an error on mobile devices.",
        "Ordering just stopped working on my site with no warning.",
    ],
    "Marketing / SEO": [
        "My Google listing is showing the wrong address. I need this fixed ASAP.",
        "My website hasn't updated since I made changes two days ago.",
        "My ranking on Google dropped significantly this month. What happened?",
        "The email campaign I scheduled yesterday never went out.",
        "My business hours on Google are still showing the old times.",
    ],
    "Product / Feature": [
        "The reporting dashboard isn't loading for me at all.",
        "I've been asking for multi-location support for months. Any update?",
        "Everything is really slow today, pages take forever to load.",
        "My Square integration stopped syncing orders since the update.",
        "I'm not receiving any notifications when new orders come in.",
    ],
    "Account Access": [
        "I can't log in. It says my password is wrong but I just reset it.",
        "My staff member can't access the dashboard even though I invited them.",
        "My account got locked and I don't know why.",
        "I'm getting an error when trying to add a new team member.",
        "The two-factor authentication code isn't being sent to my phone.",
    ],
    "Onboarding": [
        "I'm trying to connect my POS but I keep getting an error during setup.",
        "I need help getting my custom domain pointed to my Owner site.",
        "How do I import my existing menu? I can't figure out the format.",
        "My site still isn't published after completing setup. What's missing?",
        "Can someone walk me through how to set up my first email campaign?",
    ],
}

SENTIMENT_OPTIONS = ["Positive", "Neutral", "Frustrated", "Angry"]
SENTIMENT_WEIGHTS_BY_PRIMARY = {
    "Billing":            [0.05, 0.15, 0.40, 0.40],
    "Online Ordering":    [0.05, 0.20, 0.45, 0.30],
    "Marketing / SEO":    [0.10, 0.35, 0.40, 0.15],
    "Product / Feature":  [0.10, 0.30, 0.40, 0.20],
    "Account Access":     [0.05, 0.25, 0.45, 0.25],
    "Onboarding":         [0.15, 0.40, 0.30, 0.15],
}

CHANNEL_OPTIONS = ["Email", "Chat", "Phone"]
STATUS_OPTIONS = ["Open", "In Progress", "Resolved", "Escalated"]
STATUS_WEIGHTS = [0.15, 0.20, 0.55, 0.10]


def random_date(start_days_ago=180, end_days_ago=0):
    delta = random.randint(end_days_ago, start_days_ago)
    return (datetime.today() - timedelta(days=delta)).strftime("%Y-%m-%d")


def generate_user_id(i):
    return f"USR-{str(i).zfill(5)}"


def main():
    rows = []

    for i in range(1, NUM_CUSTOMERS + 1):
        user_id = generate_user_id(i)
        plan_type = random.choices(PLAN_TYPES, weights=PLAN_WEIGHTS)[0]
        is_churned = random.random() < 0.30

        num_tickets = random.randint(*TICKETS_PER_CUSTOMER_RANGE)
        # Churned and at-risk customers submit more tickets
        if is_churned:
            num_tickets = random.randint(2, 7)

        for _ in range(num_tickets):
            ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
            primary = random.choice(list(TAXONOMY.keys()))
            secondary = random.choice(list(TAXONOMY[primary].keys()))
            tertiary = random.choice(TAXONOMY[primary][secondary])
            body = random.choice(TICKET_TEMPLATES[primary])
            sentiment = random.choices(
                SENTIMENT_OPTIONS,
                weights=SENTIMENT_WEIGHTS_BY_PRIMARY[primary]
            )[0]
            channel = random.choice(CHANNEL_OPTIONS)
            status = random.choices(STATUS_OPTIONS, weights=STATUS_WEIGHTS)[0]
            created_at = random_date()

            rows.append({
                "ticket_id": ticket_id,
                "user_id": user_id,
                "plan_type": plan_type,
                "is_churned": is_churned,
                "channel": channel,
                "status": status,
                "sentiment": sentiment,
                "primary_label": primary,
                "secondary_label": secondary,
                "tertiary_label": tertiary,
                "ticket_body": body,
                "created_at": created_at,
            })

    random.shuffle(rows)

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Generated {len(rows)} support tickets for {NUM_CUSTOMERS} customers → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
