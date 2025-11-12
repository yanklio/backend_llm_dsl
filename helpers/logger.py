class Logger:
    def __init__(self, log_level):
        self.log_level = log_level

    def log(self, message):
        if self.log_level == "START":
            print(f"| START: {message}")
        elif self.log_level == "END":
            print(f"| END: {message}\n\n")
        elif self.log_level == "SUCCESS":
            print(f"✓ SUCCESS: {message}")
        elif self.log_level == "DEBUG":
            print(f"! DEBUG: {message}")
        elif self.log_level == "INFO":
            print(f"! INFO: {message}")
        elif self.log_level == "WARNING":
            print(f"⚠ WARNING: {message}")
        elif self.log_level == "ERROR":
            print(f"⚠  ERROR: {message}")
        else:
            print(f"? UNKNOWN: {message}")


default_logger = Logger("INFO")


@classmethod
def start(cls, message):
    default_logger.log_level = "START"
    default_logger.log(message)


@classmethod
def end(cls, message):
    default_logger.log_level = "END"
    default_logger.log(message)


@classmethod
def success(cls, message):
    default_logger.log_level = "SUCCESS"
    default_logger.log(message)


@classmethod
def debug(cls, message):
    default_logger.log_level = "DEBUG"
    default_logger.log(message)


@classmethod
def info(cls, message):
    default_logger.log_level = "INFO"
    default_logger.log(message)


@classmethod
def warning(cls, message):
    default_logger.log_level = "WARNING"
    default_logger.log(message)


@classmethod
def error(cls, message):
    default_logger.log_level = "ERROR"
    default_logger.log(message)


# Attach class methods to Logger class
Logger.start = start
Logger.end = end
Logger.success = success
Logger.debug = debug
Logger.info = info
Logger.warning = warning
Logger.error = error
