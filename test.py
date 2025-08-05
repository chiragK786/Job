import pandas as pd

# Define test cases as a list of dictionaries
test_cases = [
    # Coupon Creation – Basic Scenarios
    {"TC ID": "TC01", "Test Case Description": "Create a venue-specific coupon", "Steps": "Go to Admin → Coupons → Create Coupon → Select Venue filter", "Expected Result": "Coupon created with venue filter only"},
    {"TC ID": "TC02", "Test Case Description": "Create an event-specific coupon", "Steps": "Select Event filter only", "Expected Result": "Coupon created and applies only to selected events"},
    {"TC ID": "TC03", "Test Case Description": "Create a user-specific coupon", "Steps": "Select specific users only", "Expected Result": "Coupon is only valid for selected users"},
    {"TC ID": "TC04", "Test Case Description": "Create a coupon with Venue + User filters", "Steps": "Select Venue + User filter", "Expected Result": "Coupon applies only if both conditions match"},
    {"TC ID": "TC05", "Test Case Description": "Create a coupon with Event + User filters", "Steps": "Select Event + User filter", "Expected Result": "Coupon applies only for specified users on given events"},
    {"TC ID": "TC06", "Test Case Description": "Enable ‘Visible on App’", "Steps": "Enable toggle while creating user coupon", "Expected Result": "Coupon is shown in app for selected users"},
    {"TC ID": "TC07", "Test Case Description": "Disable ‘Visible on App’", "Steps": "Disable toggle while creating user coupon", "Expected Result": "Coupon is not visible in app, but remains functional"},

    # Coupon Application – Functional Scenarios
    {"TC ID": "TC08", "Test Case Description": "Apply venue-only coupon during venue booking", "Steps": "Use eligible venue, attempt coupon", "Expected Result": "Coupon applies successfully"},
    {"TC ID": "TC09", "Test Case Description": "Apply event-only coupon during event booking", "Steps": "Use eligible event", "Expected Result": "Coupon applies successfully"},
    {"TC ID": "TC10", "Test Case Description": "Apply user-only coupon", "Steps": "Logged in as eligible user, try coupon", "Expected Result": "Coupon applies"},
    {"TC ID": "TC11", "Test Case Description": "Apply Venue + User coupon with correct match", "Steps": "Match both venue and user", "Expected Result": "Coupon applies"},
    {"TC ID": "TC12", "Test Case Description": "Apply Venue + User coupon with mismatch", "Steps": "Mismatch either venue or user", "Expected Result": "Coupon not applicable"},
    {"TC ID": "TC13", "Test Case Description": "Apply Event + User coupon with correct match", "Steps": "Match both event and user", "Expected Result": "Coupon applies"},
    {"TC ID": "TC14", "Test Case Description": "Apply Event + User coupon with mismatch", "Steps": "Mismatch either event or user", "Expected Result": "Coupon not applicable"},
    {"TC ID": "TC15", "Test Case Description": "Apply expired coupon", "Steps": "Set past expiry date", "Expected Result": "Coupon fails with message “Coupon expired”"},
    {"TC ID": "TC16", "Test Case Description": "Apply future coupon", "Steps": "Set future start date", "Expected Result": "Coupon fails with “Coupon not yet active”"},
    {"TC ID": "TC17", "Test Case Description": "Use coupon exceeding usage limit", "Steps": "Exceed usage count", "Expected Result": "Show error “Usage limit exceeded”"},

    # Coupon Visibility & UI Validations
    {"TC ID": "TC18", "Test Case Description": "Check visibility of user coupon on app (when enabled)", "Steps": "Enable ‘Visible on App’ for selected user", "Expected Result": "Coupon appears in user's app interface"},
    {"TC ID": "TC19", "Test Case Description": "Check invisibility of user coupon (when disabled)", "Steps": "Disable ‘Visible on App’", "Expected Result": "Coupon not visible in user account"},
    {"TC ID": "TC20", "Test Case Description": "Ensure coupon dropdown doesn’t show unqualified coupons", "Steps": "Use different user/venue/event", "Expected Result": "Irrelevant coupons are hidden"},
    {"TC ID": "TC21", "Test Case Description": "Validate coupon details on UI", "Steps": "Hover or click on coupon", "Expected Result": "Correct metadata shown (validity, usage rules, etc.)"},

    # Edge Cases & Negative Testing
    {"TC ID": "TC22", "Test Case Description": "Apply wrong coupon for venue", "Steps": "Select ineligible venue", "Expected Result": "Show “Coupon not valid for this venue”"},
    {"TC ID": "TC23", "Test Case Description": "Apply wrong coupon for event", "Steps": "Select ineligible event", "Expected Result": "Show “Coupon not valid for this event”"},
    {"TC ID": "TC24", "Test Case Description": "Apply wrong coupon for user", "Steps": "Use user not in filter", "Expected Result": "Show “Coupon not valid for this user”"},
    {"TC ID": "TC25", "Test Case Description": "Apply a deleted coupon", "Steps": "Delete from admin, then try", "Expected Result": "Show “Coupon does not exist”"},
    {"TC ID": "TC26", "Test Case Description": "Apply inactive coupon", "Steps": "Mark coupon as inactive", "Expected Result": "Coupon fails silently or shows inactive status"},
    {"TC ID": "TC27", "Test Case Description": "Combine coupon with already discounted booking", "Steps": "Apply on discounted event/venue", "Expected Result": "Check if allowed or blocked as per rules"},
    {"TC ID": "TC28", "Test Case Description": "Validate backend API response for coupon application", "Steps": "Hit API directly with coupon & user/event/venue ID", "Expected Result": "Response should match frontend logic"},

    # Admin Config & API
    {"TC ID": "TC29", "Test Case Description": "Admin can edit coupon filters", "Steps": "Open existing coupon → edit filters", "Expected Result": "Coupon updates successfully"},
    {"TC ID": "TC30", "Test Case Description": "Admin can deactivate coupon", "Steps": "Deactivate from panel", "Expected Result": "Coupon instantly stops working"},
    {"TC ID": "TC31", "Test Case Description": "Get coupons via API (user+event+venue)", "Steps": "Use API with filters", "Expected Result": "Only qualified coupons returned"},
    {"TC ID": "TC32", "Test Case Description": "API returns correct visibility info", "Steps": "Fetch API for visible coupons", "Expected Result": "Matches UI visibility"},
]

# Convert to DataFrame
df = pd.DataFrame(test_cases)

# Save to Excel
file_path = "/mnt/data/Dynamic_Coupon_Test_Cases.xlsx"
df.to_excel(file_path, index=False)



# Define test cases as a list of dictionaries
test_cases = [
    # Coupon Creation – Basic Scenarios
    {"TC ID": "TC01", "Test Case Description": "Create a venue-specific coupon", "Steps": "Go to Admin → Coupons → Create Coupon → Select Venue filter", "Expected Result": "Coupon created with venue filter only"},
    {"TC ID": "TC02", "Test Case Description": "Create an event-specific coupon", "Steps": "Select Event filter only", "Expected Result": "Coupon created and applies only to selected events"},
    {"TC ID": "TC03", "Test Case Description": "Create a user-specific coupon", "Steps": "Select specific users only", "Expected Result": "Coupon is only valid for selected users"},
    {"TC ID": "TC04", "Test Case Description": "Create a coupon with Venue + User filters", "Steps": "Select Venue + User filter", "Expected Result": "Coupon applies only if both conditions match"},
    {"TC ID": "TC05", "Test Case Description": "Create a coupon with Event + User filters", "Steps": "Select Event + User filter", "Expected Result": "Coupon applies only for specified users on given events"},
    {"TC ID": "TC06", "Test Case Description": "Enable ‘Visible on App’", "Steps": "Enable toggle while creating user coupon", "Expected Result": "Coupon is shown in app for selected users"},
    {"TC ID": "TC07", "Test Case Description": "Disable ‘Visible on App’", "Steps": "Disable toggle while creating user coupon", "Expected Result": "Coupon is not visible in app, but remains functional"},

    # Coupon Application – Functional Scenarios
    {"TC ID": "TC08", "Test Case Description": "Apply venue-only coupon during venue booking", "Steps": "Use eligible venue, attempt coupon", "Expected Result": "Coupon applies successfully"},
    {"TC ID": "TC09", "Test Case Description": "Apply event-only coupon during event booking", "Steps": "Use eligible event", "Expected Result": "Coupon applies successfully"},
    {"TC ID": "TC10", "Test Case Description": "Apply user-only coupon", "Steps": "Logged in as eligible user, try coupon", "Expected Result": "Coupon applies"},
    {"TC ID": "TC11", "Test Case Description": "Apply Venue + User coupon with correct match", "Steps": "Match both venue and user", "Expected Result": "Coupon applies"},
    {"TC ID": "TC12", "Test Case Description": "Apply Venue + User coupon with mismatch", "Steps": "Mismatch either venue or user", "Expected Result": "Coupon not applicable"},
    {"TC ID": "TC13", "Test Case Description": "Apply Event + User coupon with correct match", "Steps": "Match both event and user", "Expected Result": "Coupon applies"},
    {"TC ID": "TC14", "Test Case Description": "Apply Event + User coupon with mismatch", "Steps": "Mismatch either event or user", "Expected Result": "Coupon not applicable"},
    {"TC ID": "TC15", "Test Case Description": "Apply expired coupon", "Steps": "Set past expiry date", "Expected Result": "Coupon fails with message “Coupon expired”"},
    {"TC ID": "TC16", "Test Case Description": "Apply future coupon", "Steps": "Set future start date", "Expected Result": "Coupon fails with “Coupon not yet active”"},
    {"TC ID": "TC17", "Test Case Description": "Use coupon exceeding usage limit", "Steps": "Exceed usage count", "Expected Result": "Show error “Usage limit exceeded”"},

    # Coupon Visibility & UI Validations
    {"TC ID": "TC18", "Test Case Description": "Check visibility of user coupon on app (when enabled)", "Steps": "Enable ‘Visible on App’ for selected user", "Expected Result": "Coupon appears in user's app interface"},
    {"TC ID": "TC19", "Test Case Description": "Check invisibility of user coupon (when disabled)", "Steps": "Disable ‘Visible on App’", "Expected Result": "Coupon not visible in user account"},
    {"TC ID": "TC20", "Test Case Description": "Ensure coupon dropdown doesn’t show unqualified coupons", "Steps": "Use different user/venue/event", "Expected Result": "Irrelevant coupons are hidden"},
    {"TC ID": "TC21", "Test Case Description": "Validate coupon details on UI", "Steps": "Hover or click on coupon", "Expected Result": "Correct metadata shown (validity, usage rules, etc.)"},

    # Edge Cases & Negative Testing
    {"TC ID": "TC22", "Test Case Description": "Apply wrong coupon for venue", "Steps": "Select ineligible venue", "Expected Result": "Show “Coupon not valid for this venue”"},
    {"TC ID": "TC23", "Test Case Description": "Apply wrong coupon for event", "Steps": "Select ineligible event", "Expected Result": "Show “Coupon not valid for this event”"},
    {"TC ID": "TC24", "Test Case Description": "Apply wrong coupon for user", "Steps": "Use user not in filter", "Expected Result": "Show “Coupon not valid for this user”"},
    {"TC ID": "TC25", "Test Case Description": "Apply a deleted coupon", "Steps": "Delete from admin, then try", "Expected Result": "Show “Coupon does not exist”"},
    {"TC ID": "TC26", "Test Case Description": "Apply inactive coupon", "Steps": "Mark coupon as inactive", "Expected Result": "Coupon fails silently or shows inactive status"},
    {"TC ID": "TC27", "Test Case Description": "Combine coupon with already discounted booking", "Steps": "Apply on discounted event/venue", "Expected Result": "Check if allowed or blocked as per rules"},
    {"TC ID": "TC28", "Test Case Description": "Validate backend API response for coupon application", "Steps": "Hit API directly with coupon & user/event/venue ID", "Expected Result": "Response should match frontend logic"},

    # Admin Config & API
    {"TC ID": "TC29", "Test Case Description": "Admin can edit coupon filters", "Steps": "Open existing coupon → edit filters", "Expected Result": "Coupon updates successfully"},
    {"TC ID": "TC30", "Test Case Description": "Admin can deactivate coupon", "Steps": "Deactivate from panel", "Expected Result": "Coupon instantly stops working"},
    {"TC ID": "TC31", "Test Case Description": "Get coupons via API (user+event+venue)", "Steps": "Use API with filters", "Expected Result": "Only qualified coupons returned"},
    {"TC ID": "TC32", "Test Case Description": "API returns correct visibility info", "Steps": "Fetch API for visible coupons", "Expected Result": "Matches UI visibility"},
]

# Convert to DataFrame
df = pd.DataFrame(test_cases)

# Save to Excel
file_path = "/mnt/data/Dynamic_Coupon_Test_Cases.xlsx"
df.to_excel(file_path, index=False)

print(file_path)

