
function contentCall(item){
    var evt = document.createEvent("CustomEvent")
    evt.initCustomEvent(item.type, true, true, item.data)
    document.dispatchEvent(evt)
}

window.addEventListener("CONTENT_EVT", async function(event){
    const item = event.detail

    // window

    if(item.type === 'foo'){
        console.log(event)
    }
})
