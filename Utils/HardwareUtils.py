import wmi, re


class HardwareUtils:
    PRIORITY = {0x10DE: 3, 0x1002: 2, 0x8086: 1}

    @staticmethod
    def get_best_gpu():
        c = wmi.WMI()
        gpus = []

        for gpu in c.Win32_VideoController():
            try:
                raw_memory = gpu.AdapterRAM
                if not raw_memory:
                    continue

                mem_bytes = int(raw_memory)
                if mem_bytes <= 0:
                    try:
                        mem_bytes = get_gpu_memory_alternative(gpu)
                    except:
                        continue

                mem_mb = mem_bytes // (1024 * 1024)

            except (ValueError, AttributeError):
                continue

            vendor_id = "0"
            device_id = "0"
            if gpu.PNPDeviceID:
                ven_match = re.search(r'VEN_([0-9A-Fa-f]{4})', gpu.PNPDeviceID)
                dev_match = re.search(r'DEV_([0-9A-Fa-f]{4})', gpu.PNPDeviceID)
                if ven_match:
                    vendor_id = int(ven_match.group(1), 16)
                if dev_match:
                    device_id = int(dev_match.group(1), 16)

            gpus.append({
                "VendorID": vendor_id,
                "DeviceID": device_id,
                "MemoryMB": mem_mb,
                "Priority": HardwareUtils.PRIORITY.get(vendor_id, 0)
            })

        if not gpus:
            return {"VendorID": "0", "DeviceID": "0"}

        # Сортируем сначала по приоритету производителя, потом по памяти
        gpu_best = max(gpus, key=lambda x: (x["Priority"], x["MemoryMB"]))
        return {"VendorID": gpu_best["VendorID"], "DeviceID": gpu_best["DeviceID"]}