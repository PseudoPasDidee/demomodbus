"""Serveur Modbus TCP avec simulation de température.

================================================================================
CARTE MÉMOIRE MODBUS — AUTOMATE SIMULÉ (new_server.py)
================================================================================
Serveur   : Modbus TCP, 0.0.0.0:5020
Device ID : 1

| Zone | Adr | Type            | Accès      | Description                                      | Initial |
|------|-----|-----------------|------------|--------------------------------------------------|---------|
| CO   | 0   | Bit (booléen)   | Lecture/Écriture | Commande chauffage (new_client_on/off.py)   | False   |
| DI   | 0   | Bit (booléen)   | Lecture    | Température > 22,0 °C (seuil haut)               | False   |
| DI   | 1   | Bit (booléen)   | Lecture    | Température < 15,0 °C (seuil bas)                | False   |
| HR   | 0   | Registre (16b)  | Lecture/Écriture | Registre de maintien (non utilisé)          | 0       |
| IR   | 0   | Registre (16b)  | Lecture    | Température × 10 (ex. 205 = 20,5 °C)             | 200     |

Légende : CO = Coils, DI = Discrete Inputs, HR = Holding Registers,
          IR = Input Registers.

La température varie entre 10,0 °C et 30,0 °C :
  - chauffage ON  -> +0,1 à +0,5 °C par cycle (1 s)
  - chauffage OFF -> -0,1 à -0,3 °C par cycle (1 s)
================================================================================
"""

import asyncio
import random

from pymodbus.server import ModbusTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice

from pymodbus import pymodbus_apply_logging_config
pymodbus_apply_logging_config("DEBUG")

DEVICE_ID = 1
ADDRESS = ("0.0.0.0", 5020)

READ_COILS = 1
READ_DISCRETE_INPUTS = 2
READ_INPUT_REGISTERS = 4

CO_HEATING = 0
DI_HIGH_TEMP = 0
DI_LOW_TEMP = 1
IR_TEMPERATURE = 0

TEMP_START = 20.0
TEMP_MIN = 10.0
TEMP_MAX = 30.0
TEMP_HIGH = 22.0
TEMP_LOW = 15.0


def build_device() -> SimDevice:
    """Décrit les 4 blocs de données du serveur."""
    return SimDevice(
        id=DEVICE_ID,
        simdata=(
            [SimData(CO_HEATING, values=False, datatype=DataType.BITS)],
            [
                SimData(DI_HIGH_TEMP, values=False, datatype=DataType.BITS),
                SimData(DI_LOW_TEMP, values=False, datatype=DataType.BITS),
            ],
            [SimData(0, values=0, datatype=DataType.REGISTERS)],
            [SimData(IR_TEMPERATURE, values=int(TEMP_START * 10), datatype=DataType.REGISTERS)],
        ),
    )


async def temperature_simulation(server: ModbusTcpServer) -> None:
    """Fait varier la température selon l'état du chauffage."""
    temperature = TEMP_START

    while True:
        heating_on = (
            await server.async_getValues(DEVICE_ID, READ_COILS, CO_HEATING, count=1)
        )[0]

        temperature += (
            random.uniform(0.1, 0.5) if heating_on else -random.uniform(0.1, 0.3)
        )
        temperature = min(max(temperature, TEMP_MIN), TEMP_MAX)

        await server.async_setValues(
            DEVICE_ID, READ_INPUT_REGISTERS, IR_TEMPERATURE, [int(temperature * 10)]
        )
        await server.async_setValues(
            DEVICE_ID, READ_DISCRETE_INPUTS, DI_HIGH_TEMP, [temperature > TEMP_HIGH]
        )
        await server.async_setValues(
            DEVICE_ID, READ_DISCRETE_INPUTS, DI_LOW_TEMP, [temperature < TEMP_LOW]
        )

        print(f"T = {temperature:.1f} °C | Chauffage = {'ON' if heating_on else 'OFF'}")
        await asyncio.sleep(1)


async def main() -> None:
    server = ModbusTcpServer(build_device(), address=ADDRESS)
    await server.serve_forever(background=True)

    print("Serveur Modbus TCP démarré sur le port 5020...")
    await temperature_simulation(server)


if __name__ == "__main__":
    asyncio.run(main())
