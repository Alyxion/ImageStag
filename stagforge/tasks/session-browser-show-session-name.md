# Show Session Name in Session Browser When "Current" Selected

## Description
When selecting "current" session in the session browser, the actual session name/ID is not displayed anywhere. Users should be able to see which session they are working with.

## Current Behavior
- User selects "current" as session
- No indication of what the actual session ID is

## Expected Behavior
- Display the resolved session name/ID somewhere visible
- Could be in header, status bar, or info panel
- Show "Current Session: abc123..." or similar

## Implementation Notes
- When "current" is selected, resolve to actual session ID
- Display in appropriate UI location
- Consider adding copy button for easy sharing of session ID
