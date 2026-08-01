let latitude = "";
let longitude = "";
let stream = null;

const map = L.map("map").setView([20.5937, 78.9629], 5);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "© OpenStreetMap"
}).addTo(map);

let marker;

map.on("click", function (e) {
  latitude = e.latlng.lat;
  longitude = e.latlng.lng;

  if (marker) map.removeLayer(marker);
  marker = L.marker([latitude, longitude]).addTo(map);
});


const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const resultImage = document.getElementById("resultImage");
const confidenceText = document.getElementById("confidence");
const statusText = document.getElementById("status");

// ---------- LOCATION ----------
function getLocation() {
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      latitude = pos.coords.latitude;
      longitude = pos.coords.longitude;
      statusText.innerText = "Location captured";
    },
    () => {
      statusText.innerText = "Location denied";
    }
  );
}

// ---------- IMAGE UPLOAD ----------
function submitUpload() {
  const imageInput = document.getElementById("image");
  if (!imageInput.files.length) {
    alert("Please select an image");
    return;
  }
  sendToBackend(imageInput.files[0], imageInput.files[0].name);
}

// ---------- CAMERA ----------
function startCamera() {
  navigator.mediaDevices.getUserMedia({ video: true })
    .then(s => {
      stream = s;
      video.srcObject = stream;
    })
    .catch(() => alert("Camera access denied"));
}

function capturePhoto() {
  if (!stream) {
    alert("Camera not started");
    return;
  }

  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  canvas.toBlob(blob => {
    sendToBackend(blob, "camera.jpg");
  }, "image/jpeg");

  stream.getTracks().forEach(t => t.stop());
  video.srcObject = null;
}

// ---------- SEND TO BACKEND ----------
function sendToBackend(imageBlob, filename) {
  const comment = document.getElementById("comment").value;
  const manualLocation = document.getElementById("manualLocation").value;
  const damageType = document.getElementById("damageType").value;

  const formData = new FormData();
  formData.append("file", imageBlob, filename);
  formData.append("issue_type", damageType);
  formData.append("comment", comment);
  formData.append("latitude", latitude);
  formData.append("longitude", longitude);
  formData.append("manual_location", manualLocation);

  statusText.innerText = "Detecting...";

  fetch("/detect", {
    method: "POST",
    body: formData
  })
    .then(res => res.json())
    .then(data => {
      if (data.count > 0 && data.image_url) {
        statusText.innerText = `${damageType} detected`;

        resultImage.src = data.image_url + "?t=" + Date.now();
        resultImage.style.display = "block";

        confidenceText.innerText =
          "Confidence: " + data.confidence;
      } else {
        statusText.innerText = "No issue detected";
        resultImage.style.display = "none";
        confidenceText.innerText = "";
      }
    })
    .catch(err => {
      console.error(err);
      statusText.innerText = "Detection failed";
      resultImage.style.display = "none";
      confidenceText.innerText = "";
    });
}
  