
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

