

const executeButton = document.getElementById("executeButton");
executeButton.addEventListener("click", async function() {
  const inputNumber = document.getElementById("inputNumber").value;
  runScript(getCode)
});

function getCode(){
  document.getElementById("query").value = 'qwe'
}

async function getCurrentTab() {
  let queryOptions = { active: true, currentWindow: true };
  // `tab` will either be a `tabs.Tab` instance or `undefined`.
  let [tab] = await chrome.tabs.query(queryOptions);
  return tab;
}

async function runScript(functionName) {
  let tab = await getCurrentTab()

  chrome.scripting.executeScript({
    target: {tabId: tab.id},
    function: functionName,
  });
}
