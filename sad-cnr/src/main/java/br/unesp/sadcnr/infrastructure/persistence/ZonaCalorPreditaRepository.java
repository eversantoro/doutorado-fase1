package br.unesp.sadcnr.infrastructure.persistence;

import br.unesp.sadcnr.domain.ZonaCalorPredita;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ZonaCalorPreditaRepository extends JpaRepository<ZonaCalorPredita, Long> {
}
