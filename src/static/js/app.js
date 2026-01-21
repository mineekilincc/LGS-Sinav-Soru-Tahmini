// LGS Soru Üretim Sistemi - JavaScript (Temizlenmiş)

document.addEventListener('DOMContentLoaded', function () {
    // Elements
    const konuSelect = document.getElementById('konu');
    const altKonuSelect = document.getElementById('alt-konu');
    const diffButtons = document.querySelectorAll('.diff-btn');
    const generateBtn = document.getElementById('generate-btn');
    const loader = document.getElementById('loader');
    const questionCard = document.getElementById('question-card');
    const placeholder = document.getElementById('placeholder');
    const promptFallback = document.getElementById('prompt-fallback');
    const modeBadge = document.getElementById('mode-badge');
    const showAnswerBtn = document.getElementById('show-answer-btn');
    const answerReveal = document.getElementById('answer-reveal');

    // State
    let selectedZorluk = 'orta';

    // Alt konuları yükle
    async function loadAltKonular(konu) {
        try {
            const response = await fetch(`/api/alt-konular/${encodeURIComponent(konu)}`);
            const altKonular = await response.json();

            altKonuSelect.innerHTML = '';
            altKonular.forEach(ak => {
                const option = document.createElement('option');
                option.value = ak;
                option.textContent = ak;
                altKonuSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Alt konu yükleme hatası:', error);
        }
    }

    // Konu değiştiğinde
    konuSelect.addEventListener('change', function () {
        loadAltKonular(this.value);
    });

    // Zorluk butonları
    diffButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            diffButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            selectedZorluk = this.dataset.value;
        });
    });

    // Soru üret
    generateBtn.addEventListener('click', async function () {
        const konu = konuSelect.value;
        const altKonu = altKonuSelect.value;

        console.log('Soru üretiliyor...', { konu, altKonu, zorluk: selectedZorluk });

        // UI güncelle
        generateBtn.disabled = true;
        loader.classList.remove('hidden');
        questionCard.classList.add('hidden');
        placeholder.classList.add('hidden');
        promptFallback.classList.add('hidden');
        answerReveal.classList.add('hidden');

        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    konu: konu,
                    alt_konu: altKonu,
                    zorluk: selectedZorluk
                })
            });

            const result = await response.json();
            console.log('API yanıtı:', result);

            if (result.success) {
                if (result.mode === 'generated' && result.question) {
                    // Soru üretildi - kartı göster
                    showQuestionCard(result);
                } else {
                    // Prompt modunda - fallback göster
                    showPromptFallback(result);
                }
            } else {
                alert('Soru üretilirken hata oluştu!');
            }
        } catch (error) {
            console.error('API hatası:', error);
            alert('Bağlantı hatası: ' + error.message);
        } finally {
            generateBtn.disabled = false;
            loader.classList.add('hidden');
        }
    });

    // Soru kartını göster
    function showQuestionCard(result) {
        const q = result.question;

        // Meta
        document.getElementById('q-konu').textContent = `${result.konu} / ${result.alt_konu}`;
        document.getElementById('q-zorluk').textContent = result.zorluk.toUpperCase();

        const farkindalik = document.getElementById('q-farkindalik');
        if (result.farkindalik_konusu) {
            farkindalik.textContent = `⚠️ ${result.farkindalik_konusu}`;
            farkindalik.style.display = 'inline';
        } else {
            farkindalik.style.display = 'none';
        }

        // Soru içeriği
        document.getElementById('q-metin').textContent = q.metin || '(Metin yok)';
        document.getElementById('q-soru').textContent = q.soru_koku || '-';
        document.getElementById('q-sik-a').textContent = q.sik_a || '-';
        document.getElementById('q-sik-b').textContent = q.sik_b || '-';
        document.getElementById('q-sik-c').textContent = q.sik_c || '-';
        document.getElementById('q-sik-d').textContent = q.sik_d || '-';
        document.getElementById('q-dogru').textContent = q.dogru_cevap || '-';

        // Doğru cevap renklendirme
        highlightCorrectOption(q.dogru_cevap);

        // Badge
        modeBadge.textContent = 'AI Üretimi';
        modeBadge.classList.remove('hidden');
        modeBadge.style.background = '#10b981';

        questionCard.classList.remove('hidden');
    }

    // Doğru şıkkı renklendir (gizli)
    function highlightCorrectOption(answer) {
        ['a', 'b', 'c', 'd'].forEach(letter => {
            const option = document.getElementById(`option-${letter}`);
            if (option) option.classList.remove('correct');
        });

        if (answer) {
            const correctOption = document.getElementById(`option-${answer.toLowerCase()}`);
            if (correctOption) {
                correctOption.dataset.correct = 'true';
            }
        }
    }

    // Cevabı göster
    if (showAnswerBtn) {
        showAnswerBtn.addEventListener('click', function () {
            answerReveal.classList.toggle('hidden');

            // Doğru şıkkı yeşil yap
            const answer = document.getElementById('q-dogru').textContent;
            if (answer && !answerReveal.classList.contains('hidden')) {
                const correctOption = document.getElementById(`option-${answer.toLowerCase()}`);
                if (correctOption) {
                    correctOption.classList.add('correct');
                }
            } else {
                ['a', 'b', 'c', 'd'].forEach(letter => {
                    const opt = document.getElementById(`option-${letter}`);
                    if (opt) opt.classList.remove('correct');
                });
            }
        });
    }

    // Prompt fallback göster
    function showPromptFallback(result) {
        const fallbackPrompt = document.getElementById('fallback-prompt');
        if (fallbackPrompt) {
            fallbackPrompt.textContent = result.prompt;
        }
        promptFallback.classList.remove('hidden');

        modeBadge.textContent = 'Prompt Modu';
        modeBadge.classList.remove('hidden');
        modeBadge.style.background = '#f59e0b';
    }

    // İlk yükleme
    loadAltKonular(konuSelect.value);

    console.log('LGS Soru Üretim Sistemi hazır!');
});
