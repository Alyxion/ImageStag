# closeAllMenus is not a function Error

## Description
Clicking certain menu items causes a JavaScript error because `closeAllMenus` is not defined or not a function.

## Error
```
(index):86 TypeError: closeAllMenus is not a function
    at onClick (eval at us (vue.esm-browser.prod.js:1:1), <anonymous>:2518:92)
    at t1 (vue.esm-browser.prod.js:5:21583)
    at t2 (vue.esm-browser.prod.js:5:21651)
    at HTMLDivElement.n (vue.esm-browser.prod.js:6:64783)
```

## Steps to Reproduce
1. Open a menu in the menu bar
2. Click on a specific menu item (need to identify which one)
3. Error appears in console

## Likely Cause
A menu item's click handler references `closeAllMenus()` but the method is not available in the current scope or not defined in the component.

## Affected Files
- `stagforge/canvas_editor.js` (menu definitions)
