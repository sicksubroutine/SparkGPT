window.onload = function() {
  const messageBox = document.getElementById('message-box');
  messageBox.scrollTop = messageBox.scrollHeight;
  const textarea = document.querySelector(".input-box")
  const submitButton = document.getElementById("submit-btn");
  textarea.addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
      event.preventDefault(); 
      submitButton.click();
    }
  });
};

function sendMessage(event) {
  event.preventDefault();
  const csrf_token = document.querySelector('input[name="_csrf_token"]').value;
  const message = document.querySelector('textarea[name="message"]').value;
  const messageBox = document.getElementById('message-box');
  const userDiv = document.createElement('div');
  const userMessage = document.createElement('div');
  const delUserMessage = document.createElement('div');
  userDiv.classList.add('flex', 'flex-col', 'items-end');
  userMessage.classList.add('max-w-sm', 'ml-auto', 'py-2', 'px-4', 'rounded-lg', 'bg-green-700', 'text-white');
  userDiv.appendChild(userMessage);
  userDiv.appendChild(delUserMessage);
  userMessage.textContent = message;
  messageBox.appendChild(userDiv);
  
  const assistantDiv = document.createElement('div');
  const assistantMessage = document.createElement('div');
  const delAssistantMessage = document.createElement('div');
  assistantDiv.classList.add('flex', 'flex-col', 'items-start');
  assistantMessage.innerHTML = '<i class="fas fa-spinner fa-pulse"></i>';
  assistantMessage.classList.add('max-w-sm', 'mx-2', 'py-2', 'px-4', 'rounded-lg', 'bg-blue-700', 'text-white');
  assistantDiv.appendChild(assistantMessage);
  assistantDiv.appendChild(delAssistantMessage);
  messageBox.appendChild(assistantDiv);
  
  const formData = new FormData();
  formData.append('message', message);
  formData.append('_csrf_token', csrf_token);
  const sats = document.getElementById('sats');
  
  fetch('/respond', {
    method: 'POST',
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    if (data.over_balance == true) {
      window.location.reload();
    }
    assistantMessage.innerHTML = data.response;
    sats.innerHTML = data.sats;
    delUserMessage.innerHTML = data.user_string;
    delAssistantMessage.innerHTML = data.assistant_string;
    Prism.highlightAll();
    messageBox.scrollTop = messageBox.scrollHeight;
  });
 
  document.querySelector('textarea[name="message"]').value = '';
  messageBox.scrollTop = messageBox.scrollHeight;
}


