CREATE DATABASE IF NOT EXISTS `medidor2` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE `medidor2`;

-- Local da instalação/coleta
DROP TABLE IF EXISTS `local_instalacao`;
CREATE TABLE `local_instalacao` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `nome` VARCHAR(80) NOT NULL,
  `descricao` VARCHAR(255) DEFAULT NULL,
  `latitude`  DECIMAL(9,6) DEFAULT NULL,
  `longitude` DECIMAL(9,6) DEFAULT NULL,
  `elevacao_m` DECIMAL(8,2) DEFAULT NULL,
  `ambiente` ENUM('outdoor','indoor') DEFAULT 'outdoor',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB;

-- Dispositivo (a "caixa")
DROP TABLE IF EXISTS `dispositivo`;
CREATE TABLE `dispositivo` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `nome` VARCHAR(80) NOT NULL,
  `modelo` VARCHAR(80) DEFAULT NULL,
  `serial` VARCHAR(80) DEFAULT NULL,
  `local_id` INT DEFAULT NULL,
  `ativo` TINYINT(1) DEFAULT 1,
  `instalado_em` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_local` (`local_id`),
  CONSTRAINT `fk_dispositivo_local` FOREIGN KEY (`local_id`) REFERENCES `local_instalacao`(`id`)
    ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- Métricas possíveis (temperatura, umidade, PM2.5, etc.)
DROP TABLE IF EXISTS `metrica`;
CREATE TABLE `metrica` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `codigo` VARCHAR(40) NOT NULL,          -- ex.: temp, umid, pm25, pm10, co2, pressao, altitude
  `nome`   VARCHAR(80) NOT NULL,          -- ex.: Temperatura do ar
  `unidade` VARCHAR(20) NOT NULL,         -- ex.: °C, %, µg/m³, ppm, hPa, m
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_metrica_codigo` (`codigo`)
) ENGINE=InnoDB;

-- Sensor físico dentro do dispositivo (um por métrica, normalmente)
DROP TABLE IF EXISTS `sensor`;
CREATE TABLE `sensor` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `dispositivo_id` INT NOT NULL,
  `metrica_id` INT NOT NULL,
  `modelo` VARCHAR(80) DEFAULT NULL,      -- ex.: SDS011, SGP30, BME280
  `fabricante` VARCHAR(80) DEFAULT NULL,
  `intervalo_seg` INT DEFAULT 60,         -- intervalo de amostragem
  `valor_min` DECIMAL(12,4) DEFAULT NULL,
  `valor_max` DECIMAL(12,4) DEFAULT NULL,
  `coef_calibracao` JSON DEFAULT NULL,    -- ex.: {"a": 1.02, "b": -0.5}
  `ativo` TINYINT(1) DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `idx_sensor_disp` (`dispositivo_id`),
  KEY `idx_sensor_metrica` (`metrica_id`),
  CONSTRAINT `fk_sensor_disp` FOREIGN KEY (`dispositivo_id`) REFERENCES `dispositivo`(`id`)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT `fk_sensor_metrica` FOREIGN KEY (`metrica_id`) REFERENCES `metrica`(`id`)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Leituras ("long format")
DROP TABLE IF EXISTS `leitura`;
CREATE TABLE `leitura` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `sensor_id` INT NOT NULL,
  `ts` DATETIME NOT NULL,
  `valor_bruto` DECIMAL(12,4) DEFAULT NULL,
  `valor_corrigido` DECIMAL(12,4) DEFAULT NULL,
  `qa_flag` SET('OK','AQUECIMENTO','FORA_INTERVALO','FALHA_SENSOR','LACUNA','HIGH_UR','ANOMALIA') DEFAULT 'OK',
  PRIMARY KEY (`id`),
  KEY `idx_leitura_ts` (`ts`),
  KEY `idx_leitura_sensor_ts` (`sensor_id`,`ts`),
  CONSTRAINT `fk_leitura_sensor` FOREIGN KEY (`sensor_id`) REFERENCES `sensor`(`id`)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- Agregados horários (opcional; podem ser materializados via job ETL)
DROP TABLE IF EXISTS `agg_horaria`;
CREATE TABLE `agg_horaria` (
  `sensor_id` INT NOT NULL,
  `ts_hora` DATETIME NOT NULL,            -- arredondado para o início da hora
  `media` DECIMAL(12,4) DEFAULT NULL,
  `p95`   DECIMAL(12,4) DEFAULT NULL,
  `n_obs` INT DEFAULT 0,
  PRIMARY KEY (`sensor_id`,`ts_hora`),
  KEY `idx_agg_ts` (`ts_hora`),
  CONSTRAINT `fk_agg_sensor` FOREIGN KEY (`sensor_id`) REFERENCES `sensor`(`id`)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;


