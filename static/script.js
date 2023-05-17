document.getElementById('menu-button').addEventListener('click', function() {
  document.getElementById('sidebar').classList.toggle('translate-x-0');
});

document.addEventListener('click', function(event) {
  var isClickInside = document.getElementById('sidebar').contains(event.target);
  var isOnMenuButton = document.getElementById('menu-button').contains(event.target);
  
  if (!isClickInside && !isOnMenuButton && document.getElementById('sidebar').classList.contains('translate-x-0')) {
    document.getElementById('sidebar').classList.toggle('translate-x-0');
    }
});


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
  const message = document.querySelector('textarea[name="message"]').value;
  const messageBox = document.getElementById('message-box');
  const userMessage = document.createElement('div');
  userMessage.textContent = message;
  userMessage.classList.add('max-w-sm', 'ml-auto', 'py-2', 'px-4', 'rounded-lg', 'bg-green-700', 'text-white', 'items-end');
  messageBox.appendChild(userMessage);
  
  const assistantMessage = document.createElement('div');
  assistantMessage.innerHTML = '<i class="fas fa-spinner fa-pulse"></i>';
  assistantMessage.classList.add('max-w-sm', 'mx-2', 'py-2', 'px-4', 'rounded-lg', 'bg-blue-700', 'text-white');
  messageBox.appendChild(assistantMessage);
  
  const formData = new FormData();
  formData.append('message', message);
  
  fetch('/respond', {
    method: 'POST',
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    assistantMessage.innerHTML = data.response;
    messageBox.scrollTop = messageBox.scrollHeight;
    location.reload();
  });
  
  document.querySelector('textarea[name="message"]').value = '';
  messageBox.scrollTop = messageBox.scrollHeight;
}


