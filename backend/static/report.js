let selectedIssue = "pothole";
let lat = 20.5937;
let lon = 78.9629;
let map;
let marker;
let stream;
let selectedMode = "ai";

const previewWrap = document.getElementById("previewWrap");
const imageInput = document.getElementById("imageInput");
const statusText = document.getElementById("status");
const submitButton = document.getElementById("submitBtn");
const resultCard = document.getElementById("resultCard");
const resultImage = document.getElementById("resultImage");
const confidenceScore = document.getElementById("confidenceScore");
const issueSelect = document.getElementById("issueSelect");
const useCreditsInput = document.getElementById("useCredits");

function renderPreview(src) {
    previewWrap.innerHTML = "";
    const preview = document.createElement("img");
    preview.src = src;
    preview.alt = "Selected issue preview";
    previewWrap.appendChild(preview);
}

function initMap() {
    map = L.map("map").setView([lat, lon], 5);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    marker = L.marker([lat, lon], { draggable: true }).addTo(map);

    marker.on("dragend", () => {
        const position = marker.getLatLng();
        lat = position.lat;
        lon = position.lng;
    });

    map.on("click", (event) => {
        lat = event.latlng.lat;
        lon = event.latlng.lng;
        marker.setLatLng([lat, lon]);
    });

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                lat = position.coords.latitude;
                lon = position.coords.longitude;
                map.setView([lat, lon], 16);
                marker.setLatLng([lat, lon]);
            },
            () => {
                map.setView([lat, lon], 5);
            }
        );
    }
}

function setIssueSelection(issueKey) {
    const activeItem = document.querySelector(`.issue-item[data-type="${issueKey}"]`);
    if (!activeItem) {
        return;
    }

    document.querySelectorAll(".issue-item").forEach((button) => button.classList.remove("active"));
    activeItem.classList.add("active");
    selectedIssue = activeItem.dataset.type;
    selectedMode = activeItem.dataset.mode;
    if (issueSelect) {
        issueSelect.value = issueKey;
    }
    statusText.textContent = selectedMode === "ai"
        ? `Selected ${activeItem.dataset.label}. This image will go through AI-assisted review.`
        : `Selected ${activeItem.dataset.label}. This report will be queued for manual review because it needs human context or non-image data.`;
}

document.querySelectorAll(".issue-item").forEach((item) => {
    item.addEventListener("click", () => setIssueSelection(item.dataset.type));
});

if (issueSelect) {
    issueSelect.addEventListener("change", () => setIssueSelection(issueSelect.value));
}

imageInput.addEventListener("change", function handleImageChange() {
    const [file] = imageInput.files;
    if (file) {
        renderPreview(URL.createObjectURL(file));
    }
});

async function startCamera() {
    const cameraContainer = document.getElementById("cameraContainer");
    const video = document.getElementById("video");

    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
        video.srcObject = stream;
        cameraContainer.style.display = "block";
        statusText.textContent = "Camera ready. Capture an image when the issue is clearly visible.";
    } catch (error) {
        statusText.textContent = "Camera access is unavailable on this device or browser.";
    }
}

function capturePhoto() {
    const video = document.getElementById("video");
    const canvas = document.getElementById("canvas");
    const context = canvas.getContext("2d");

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.style.display = "block";
    renderPreview(canvas.toDataURL("image/jpeg"));

    if (stream) {
        stream.getTracks().forEach((track) => track.stop());
    }

    document.getElementById("cameraContainer").style.display = "none";
    statusText.textContent = "Captured image ready for submission.";
}

async function getImageBlob() {
    if (imageInput.files[0]) {
        return imageInput.files[0];
    }

    const canvas = document.getElementById("canvas");
    if (canvas.width > 0 && canvas.height > 0) {
        return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg"));
    }

    return null;
}

async function submitReport() {
    const imageBlob = await getImageBlob();
    const comment = document.getElementById("comment").value.trim();
    const useCredits = Boolean(useCreditsInput && useCreditsInput.checked);

    if (!imageBlob) {
        statusText.textContent = "Add an image before submitting the report.";
        return;
    }

    const formData = new FormData();
    formData.append("file", imageBlob, "report.jpg");
    formData.append("issue_type", selectedIssue);
    formData.append("comment", comment);
    formData.append("latitude", lat);
    formData.append("longitude", lon);
    formData.append("use_credits", useCredits ? "true" : "false");

    submitButton.disabled = true;
    statusText.textContent = selectedMode === "ai"
        ? "AI is analyzing the image and preparing the complaint record..."
        : "Preparing the complaint record and sending it to the manual review queue...";
    if (useCredits) {
        statusText.textContent += ` ${window.priorityRedeemCost} credits will be used for priority handling.`;
    }

    try {
        const response = await fetch("/detect", { method: "POST", body: formData });
        const result = await response.json();

        if (!response.ok) {
            statusText.textContent = result.error || "The report could not be submitted.";
            submitButton.disabled = false;
            return;
        }

        resultCard.style.display = "block";
        resultImage.src = result.image_url;
        confidenceScore.textContent = `${result.analysis_mode}: ${Math.round((result.confidence || 0) * 100)}% confidence, severity ${result.severity}.${result.priority_requested ? " Priority handling enabled." : ""}`;

        const params = new URLSearchParams({
            id: result.report_id,
            type: result.issue_label || selectedIssue,
            img: result.image_url,
            conf: result.confidence || 0,
            lat,
            lon,
            msg: comment,
            mode: result.analysis_mode || "Manual Review",
            note: result.review_note || "",
            severity: result.severity || "Needs Review"
        });

        window.location.href = `/success?${params.toString()}`;
    } catch (error) {
        statusText.textContent = "The server is unavailable right now. Please try again.";
        submitButton.disabled = false;
    }
}

initMap();
setIssueSelection(selectedIssue);
