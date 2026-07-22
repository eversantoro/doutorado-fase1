(() => {
    const svcStatus = document.getElementById("svcStatus");
    const importStatus = document.getElementById("importStatus");
    const form = document.getElementById("importForm");
    const btn = document.getElementById("btnImport");
    const reportEmpty = document.getElementById("reportEmpty");
    const reportBox = document.getElementById("reportBox");
    const schemaBox = document.getElementById("schemaBox");

    function setMsg(el, msg, ok) {
        el.textContent = msg || "";
        el.className = "status" + (ok === true ? " ok" : ok === false ? " err" : "");
    }

    async function checarServico() {
        try {
            const res = await fetch("/api/importacao/health");
            const data = await res.json();
            if (data.status === "ok") {
                setMsg(svcStatus, "Microserviço de importação online (PostGIS conectado).", true);
            } else {
                setMsg(svcStatus, "Microserviço degradado: " + (data.detail || data.database), false);
            }
        } catch (_) {
            setMsg(svcStatus, "Microserviço indisponivel. Suba o import-service na porta 8090.", false);
        }
    }

    async function carregarSchema() {
        try {
            const res = await fetch("/api/importacao/schema");
            const data = await res.json();
            schemaBox.textContent = JSON.stringify(data, null, 2);
        } catch (_) {
            schemaBox.textContent = "Nao foi possivel carregar o schema do microservico.";
        }
    }

    function preencherRelatorio(data) {
        reportEmpty.classList.add("hidden");
        reportBox.classList.remove("hidden");
        document.getElementById("rStatus").textContent = data.status || "—";
        document.getElementById("rRecv").textContent = data.recebidas ?? "—";
        document.getElementById("rOk").textContent = data.importadas ?? "—";
        document.getElementById("rFail").textContent = data.rejeitadas ?? "—";
        document.getElementById("rTotal").textContent = data.total_banco ?? "—";

        const ul = document.getElementById("rErrors");
        ul.innerHTML = "";
        const erros = data.erros || [];
        if (erros.length === 0) {
            ul.innerHTML = "<li>Nenhum erro reportado.</li>";
            return;
        }
        erros.forEach((e) => {
            const li = document.createElement("li");
            li.textContent = e.linha > 0 ? `Linha ${e.linha}: ${e.motivo}` : e.motivo;
            ul.appendChild(li);
        });
    }

    form.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const fileInput = document.getElementById("csvFile");
        if (!fileInput.files || fileInput.files.length === 0) {
            setMsg(importStatus, "Selecione um arquivo CSV.", false);
            return;
        }

        const fd = new FormData();
        fd.append("file", fileInput.files[0]);
        fd.append("modo", document.getElementById("modo").value);
        fd.append("strict", document.getElementById("strict").checked ? "true" : "false");

        btn.disabled = true;
        setMsg(importStatus, "Enviando ao microservico de importacao...", null);
        try {
            const res = await fetch("/api/importacao/pacientes", { method: "POST", body: fd });
            const body = await res.json().catch(() => ({}));
            if (!res.ok) {
                const detalhe = body.erro || body.detail || JSON.stringify(body);
                throw new Error(typeof detalhe === "string" ? detalhe : "Falha na importacao");
            }
            preencherRelatorio(body);
            setMsg(
                importStatus,
                `Concluido: ${body.importadas} importadas, ${body.rejeitadas} rejeitadas.`,
                true
            );
        } catch (err) {
            setMsg(importStatus, err.message || "Falha na importacao", false);
        } finally {
            btn.disabled = false;
        }
    });

    checarServico();
    carregarSchema();
})();
