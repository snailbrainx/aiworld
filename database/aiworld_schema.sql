-- --------------------------------------------------------
-- Host:                         xx
-- Server version:               10.8.3-MariaDB-1:10.8.3+maria~jammy - mariadb.org binary distribution
-- Server OS:                    debian-linux-gnu
-- HeidiSQL Version:             12.0.0.6536
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Dumping database structure for aiworld
CREATE DATABASE IF NOT EXISTS `aiworld` /*!40100 DEFAULT CHARACTER SET utf8mb4 */;
USE `aiworld`;

-- Dumping structure for table aiworld.aiworld
CREATE TABLE IF NOT EXISTS `aiworld` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `time` int(11) DEFAULT 0,
  `position` varchar(50) DEFAULT NULL,
  `entity` varchar(50) DEFAULT NULL,
  `thought` text DEFAULT NULL,
  `talk` text DEFAULT NULL,
  `move` varchar(50) DEFAULT NULL,
  `timestamp` datetime DEFAULT NULL,
  `health_points` int(11) DEFAULT NULL,
  `ability` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `time_entity` (`time`,`entity`),
  KEY `time` (`time`)
) ENGINE=InnoDB AUTO_INCREMENT=3193 DEFAULT CHARSET=utf8mb4;

-- Data exporting was unselected.

-- Dumping structure for table aiworld.entities
CREATE TABLE IF NOT EXISTS `entities` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL DEFAULT '0',
  `personality` text NOT NULL,
  `start_pos` varchar(50) DEFAULT NULL,
  `image` varchar(50) DEFAULT NULL,
  `ability` varchar(15) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nameunique` (`name`),
  KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4;

-- Data exporting was unselected.

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
