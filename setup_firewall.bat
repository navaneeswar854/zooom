@echo off
echo Setting up Windows Firewall rules for LAN Collaboration Suite...
echo.
echo Adding TCP port 8080 rule...
netsh advfirewall firewall add rule name="LAN Collaboration Suite TCP" dir=in action=allow protocol=TCP localport=8080
echo.
echo Adding UDP port 8081 rule...
netsh advfirewall firewall add rule name="LAN Collaboration Suite UDP" dir=in action=allow protocol=UDP localport=8081
echo.
echo Firewall rules added successfully!
echo.
echo Your server IP address is: 10.36.87.57
echo Other laptops should connect to: 10.36.87.57:8080
echo.
pause