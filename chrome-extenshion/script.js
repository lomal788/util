async function getCurrentTab() {
  let queryOptions = { active: true, currentWindow: true };
  // `tab` will either be a `tabs.Tab` instance or `undefined`.
  let [tab] = await chrome.tabs.query(queryOptions);
  return tab;
}


async function test(){
  const tab = await getCurrentTab()

  chrome.storage.local.remove('foo')
  chrome.storage.local.set({
    test:'foo'
  })

  chrome.tabs.sendMessage(tab.id, {
    type:'foo',
    data:{
      foo: 'bar'
    }
  })
}

const executeButton = document.getElementById("executeButton");
executeButton.addEventListener("click", async function() {
  const tab = await getCurrentTab()
  const inputNumber = document.getElementById("inputNumber").value;

  chrome.tabs.sendMessage(tab.id, {
    type:'foo',
    data:{
      foo: inputNumber
    }
  })

  // runScript(getCode)
});

function getCode(){
  document.getElementById("query").value = 'qwe'
}


async function runScript(functionName) {
  let tab = await getCurrentTab()

  chrome.scripting.executeScript({
    target: {tabId: tab.id},
    function: functionName,
  });
}
