package br.unesp.sadcnr.api;

import br.unesp.sadcnr.application.ImportacaoGatewayService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@RestController
@RequestMapping("/api/importacao")
@Tag(name = "Importação", description = "Gateway HTTP para o microserviço FastAPI de importação (:8090)")
public class ImportacaoController {

    private final ImportacaoGatewayService gateway;

    public ImportacaoController(ImportacaoGatewayService gateway) {
        this.gateway = gateway;
    }

    @GetMapping("/health")
    @Operation(summary = "Saúde do microserviço de importação")
    public ResponseEntity<Map<String, Object>> health() {
        return ResponseEntity.ok(gateway.health());
    }

    @GetMapping("/schema")
    @Operation(summary = "Contrato JSON de importação", description = "Colunas, bounding box e limites.")
    public ResponseEntity<Map<String, Object>> schema() {
        return ResponseEntity.ok(gateway.schema());
    }

    @GetMapping("/template")
    @Operation(summary = "Download do CSV modelo de pacientes")
    @ApiResponse(responseCode = "200", description = "Arquivo CSV",
            content = @Content(mediaType = "text/csv"))
    public ResponseEntity<byte[]> template() {
        byte[] csv = gateway.templatePacientes();
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=modelo_pacientes_psr.csv")
                .contentType(new MediaType("text", "csv"))
                .body(csv);
    }

    @PostMapping(value = "/pacientes", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @Operation(
            summary = "Importar CSV de pacientes PSR",
            description = "Encaminha o arquivo ao microserviço. Ver docs/FORMATO_IMPORTACAO_DADOS.md.")
    @ApiResponse(responseCode = "200", description = "Relatório de importação")
    @ApiResponse(responseCode = "400", description = "CSV inválido")
    @ApiResponse(responseCode = "503", description = "Microserviço indisponível")
    public ResponseEntity<Map<String, Object>> importar(
            @Parameter(description = "Arquivo CSV UTF-8") @RequestParam("file") MultipartFile file,
            @Parameter(description = "substituir | acrescentar")
            @RequestParam(value = "modo", defaultValue = "substituir") String modo,
            @Parameter(description = "Se true, aborta na primeira linha inválida")
            @RequestParam(value = "strict", defaultValue = "false") boolean strict) throws Exception {
        return ResponseEntity.ok(gateway.importarPacientes(file, modo, strict));
    }
}
