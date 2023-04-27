function injectScript(file_path, tag) {
    var node = document.getElementsByTagName(tag)[0];
    var script = document.createElement('script');
    script.setAttribute('type', 'text/javascript');
    script.setAttribute('src', file_path);
    node.appendChild(script);
}
injectScript(chrome.runtime.getURL('content.js'), 'body');

// Event content -> popup
window.addEventListener("CONTENT_CALL", async function(event){
    sendResponse(event)
  })

// Pass data, Call event Popup -> content, content -> Popup Callback
chrome.runtime.onMessage.addListener(
    function(req, sender, sendResponse) {
        var evt = document.createEvent("CustomEvent")

        window.addEventListener("CONTENT_CALLBACK", async function(event){
            sendResponse(event)
          })

        evt.initCustomEvent('CONTENT_EVT', true, true, req)
        document.dispatchEvent(evt)
});
