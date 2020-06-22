import traceback

class Debug:
	@staticmethod
	def Log(message):
		print(message)
		for line in traceback.format_stack():
			print(line.strip())