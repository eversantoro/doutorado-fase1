(() => {
    const BAURU = [-22.3149, -49.0606];
    const map = L.map("map", { zoomControl: true }).setView(BAURU, 13);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap"
    }).addTo(map);

    let heatLayer = null;

    const statusEl = document.getElementById("uploadStatus");
    const totalEl = document.getElementById("totalPacientes");
    const form = document.getElementById("uploadForm");
    const btn = document.getElementById("btnUpload");

    function setStatus(msg, ok) {
        statusEl.textContent = msg || "";
        statusEl.className = "status" + (ok === true ? " ok" : ok === false ? " err" : "");
    }

    async function atualizarContagem() {
        try {
            const res = await fetch("/api/pacientes/count");
            if (!res.ok) return;
            const data = await res.json();
            totalEl.textContent = `${data.total} pacientes`;
        } catch (_) {
            /* ignore */
        }
    }

    async function carregarHeatmap() {
        const res = await fetch("/api/pacientes/heatmap");
        if (!res.ok) {
            throw new Error("Falha ao carregar heatmap");
        }
        const pontos = await res.json();
        if (heatLayer) {
            map.removeLayer(heatLayer);
        }
        heatLayer = L.heatLayer(pontos, {
            radius: 28,
            blur: 22,
            maxZoom: 17,
            max: 1.0,
            gradient: {
                0.2: "#2b6cb0",
                0.45: "#38a169",
                0.7: "#d69e2e",
                1.0: "#c53030"
            }
        }).addTo(map);

        if (pontos.length > 0) {
            const bounds = L.latLngBounds(pontos.map((p) => [p[0], p[1]]));
            map.fitBounds(bounds.pad(0.15));
        }
        await atualizarContagem();
        return pontos.length;
    }

    form.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const fileInput = document.getElementById("csvFile");
        const limpar = document.getElementById("limpar").checked;
        if (!fileInput.files || fileInput.files.length === 0) {
            setStatus("Selecione um arquivo CSV.", false);
            return;
        }

        const fd = new FormData();
        fd.append("file", fileInput.files[0]);

        btn.disabled = true;
        setStatus("Importando...", null);
        try {
            const url = `/api/upload-csv?limpar=${limpar}`;
            const res = await fetch(url, { method: "POST", body: fd });
            const body = await res.json();
            if (!res.ok) {
                throw new Error(body.erro || "Erro no upload");
            }
            const n = await carregarHeatmap();
            setStatus(`Importados ${body.registros} registros. Heatmap com ${n} pontos.`, true);
        } catch (err) {
            setStatus(err.message || "Falha na importação", false);
        } finally {
            btn.disabled = false;
        }
    });

    carregarHeatmap()
        .then((n) => {
            if (n === 0) {
                setStatus("Nenhum dado no banco. Importe o CSV sintético para ver as zonas de calor.", null);
            }
        })
        .catch(() => setStatus("Não foi possível carregar o mapa (API offline?).", false));
})();
