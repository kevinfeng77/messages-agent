const seApp = Application('System Events')
const messagesApp = Application('Messages')
messagesApp.includeStandardAdditions = true;

// Run and get passed in arguments
ObjC.import('stdlib')                               // for exit

var args = $.NSProcessInfo.processInfo.arguments    
var argv = []
var argc = args.count
for (var i = 4; i < argc; i++) {
    // skip 3-word run command at top and this file's name
    argv.push(ObjC.unwrap(args.objectAtIndex(i)))  
}

const number = argv[0]
const message = argv[1]

sendNewMessage(number, message)

function sendNewMessage(number, message) {
    messagesApp.activate()

    // Wait for app to activate
    delay(0.5)
    
    // Create new message
    seApp.keystroke('n', {using: 'command down'})
    
    // Wait for new message window to open
    delay(0.5)
    
    // Type the phone number in To field
    seApp.keystroke(number)
    
    // Wait a bit then press Tab to move to message field
    delay(0.3)
    seApp.keyCode(48) // Tab key to move from To field to message field
    
    // Additional wait to ensure focus is in message field
    delay(0.3)
    
    // Type the message
    seApp.keystroke(message)
    
    // Wait before sending
    delay(0.2)
    
    // Send message (Enter key)
    seApp.keyCode(36)

    // Return a simple success indicator
    return "message_sent_" + Date.now()
}

// Should prevent app from quitting
function quit() {
    return true;
}

seApp.keyUp(59)
$.exit(0)