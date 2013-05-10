from bitBoard import app
import sys
if 'altPort' in sys.argv:
	portNum = 5001
else:
	portNum = 5000
if 'debug' in sys.argv:
	app.run(debug=True, port=portNum)
else:
	app.run(debug=False, host='0.0.0.0')

