const answerInput = document.getElementById("answerInput");
const wpmLabel = document.getElementById("wpmLabel");
const wordLabel = document.getElementById("wordLabel");
const typingWpmInput = document.getElementById("typingWpm");
const voiceBtn = document.getElementById("voiceBtn");

let startedAt = null;
let recognition = null;
let isListening = false;

function countWords(text) {
    return text.trim().split(/\s+/).filter(Boolean).length;
}

function updateTypingMetrics() {
    if (!startedAt) {
        startedAt = Date.now();
    }

    const words = countWords(answerInput.value);
    const elapsedMinutes = Math.max((Date.now() - startedAt) / 60000, 1 / 60);
    const wpm = Math.round(words / elapsedMinutes);

    wordLabel.textContent = String(words);
    wpmLabel.textContent = String(Number.isFinite(wpm) ? wpm : 0);
    typingWpmInput.value = String(Number.isFinite(wpm) ? wpm : 0);
}

answerInput.addEventListener("input", updateTypingMetrics);

function setupVoiceRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        voiceBtn.textContent = "Voice Input Unavailable";
        voiceBtn.disabled = true;
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.continuous = true;

    recognition.onresult = (event) => {
        let interim = "";
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                answerInput.value = `${answerInput.value} ${transcript}`.trim();
            } else {
                interim += transcript;
            }
        }
        if (interim) {
            answerInput.placeholder = `Listening: ${interim}`;
        } else {
            answerInput.placeholder = "Type your answer or use Voice Input below...";
        }
        updateTypingMetrics();
    };

    recognition.onend = () => {
        if (isListening) {
            recognition.start();
            return;
        }
        voiceBtn.textContent = "Start Voice Input";
    };
}

voiceBtn.addEventListener("click", () => {
    if (!recognition) {
        return;
    }
    if (isListening) {
        isListening = false;
        recognition.stop();
        voiceBtn.textContent = "Start Voice Input";
        answerInput.placeholder = "Type your answer or use Voice Input below...";
    } else {
        isListening = true;
        recognition.start();
        voiceBtn.textContent = "Stop Voice Input";
    }
});

setupVoiceRecognition();
