package br.unesp.sadcnr.infrastructure.persistence;

import br.unesp.sadcnr.domain.PacientePSR;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;

public interface PacientePSRRepository extends JpaRepository<PacientePSR, Long> {

    @Modifying
    @Query(value = "TRUNCATE TABLE historico_atendimentos, pacientes_psr RESTART IDENTITY CASCADE", nativeQuery = true)
    void truncatePacientes();
}
