# alterfat
## Quick format USB devices to FAT12/16/32/exFAT for Windows 7-11 x86-x64
### Быстрое форматирование карт памяти и USB-флешек в файловые системы семества FAT

![Скриншот](https://github.com/0xMihalich/alterfat/blob/main/screen.jpg?raw=true)

За основу взят код от maxpat78 https://github.com/maxpat78/FATtools

Проведен рефакторинг, оставлено только то, что нужно для форматирования

**Особенности программы:(bold)**
- Размер кластера выбирается автоматически
- Поддерживается только быстрое форматирование раздела, для Low lewel форматирования рекомендуется использовать другие программы, если это необходимо
- Программа видит всю память устройства, что является хорошим решением для форматирования памяти, которую Windows отказался форматировать по причине наличия на ней множества разделов
- Тип загрузочной записи MBR

**Отличие от стандартных средств Windows:(bold)**
- Нет лишней информации в MBR секторе (Головка, Сектор, Цилиндр), являющейся необходимой для HDD и абсолютно не нужной для устройств с NAND
- Код типа раздела в MBR явно указывает на структуру FAT для любых устройств, в отличие от Windows, указывающей том с поддержкой LBA (системы без поддержки LBA не пытаются открыть такой раздел)
- Файловая система создается сразу со второго сектора, что дает возможность использовать все доступное место
- Поддержка карт памяти и USB-флешек емкостью до 2 ТБ (2199023255552 байт)
- Метка тома поддерживает любой регистр букв
- Длина метки тома до 11 символов для FAT12/FAT16/FAT32 и до 15 символов для exFAT
- Раздел от 32.5 МБ (34089472 байт) до 2 ТБ (2199023255040 байт) разрешено форматировать в файловую систему FAT32 (карта памяти может быть использована в сотовых телефонах, регистраторах, телевизорах, nintendo 3ds/ds и других устройствах)

**Измения в версии 1.1:(bold)**
- Добавлена быстрая проверка логических дисков на принадлежность к Removable Media
- Исправлена ошибка Win32File, вызывающая исключение при чтении аттрибутов дисков
- Добавлен второй метод сканирования дисков если WBEM отказался искать диски
- Изменен текст ошибки если не удалось получить доступ к диску. Раньше программа просила проверить права администратора, теперь говорит, что диск используется другой программой, что является более правильной ситуацией

Форматирование флешки на 16 ГБ занимает буквально 2 секунды, память на 2 ТБ если она у кого-то конечно будет при форматировании займет какое-то время поскольку в раздел нужно лить 512 МБ данных

[Скачать сборку под Windows 7-11 для 32 и 64 битных систем с моего Google Disk](https://drive.google.com/file/d/1w4AGRBT4lYr3qg--Ia8ypPu-j2-Xu9bF/)
