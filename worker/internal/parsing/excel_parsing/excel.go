package excel_parsing

import (
	"fmt"
	"github.com/xuri/excelize/v2"
	"io"
	"strings"
)

// ExcelToText конвертирует Excel файл в текстовое представление
func ExcelToText(file io.Reader) (string, error) {
	f, err := excelize.OpenReader(file)
	if err != nil {
		return "", fmt.Errorf("не удалось открыть файл: %w", err)
	}
	defer func() {
		_ = f.Close()
	}()

	var result strings.Builder

	// Получаем список всех листов
	sheets := f.GetSheetList()

	// Проходимся по каждому листу
	for sheetIdx, sheetName := range sheets {
		// Заголовок листа
		_, _ = fmt.Fprintf(&result, "\n=== Лист %d: %s ===\n", sheetIdx+1, sheetName)
		//result.WriteString(fmt.Sprintf("\n=== Лист %d: %s ===\n", sheetIdx+1, sheetName))

		// Получаем все строки с текущего листа
		rows, err := f.GetRows(sheetName)
		if err != nil {
			_, _ = fmt.Fprintf(&result, "[Ошибка чтения листа: %v]\n", err)
			//result.WriteString(fmt.Sprintf("[Ошибка чтения листа: %v]\n", err))
			continue
		}

		// Проходим по каждой строке
		for rowIdx, row := range rows {
			// Номер строки
			_, _ = fmt.Fprintf(&result, "Строка %d: ", rowIdx+1)
			//result.WriteString(fmt.Sprintf("Строка %d: ", rowIdx+1))

			// Склеиваем ячейки строки через разделитель
			line := strings.Join(row, " | ")
			if strings.TrimSpace(line) == "" {
				// Пустая строка
				continue
			}
			result.WriteString(line)
			result.WriteString("\n")
		}

		// Добавляем пустую строку между листами
		result.WriteString("\n")
	}

	return result.String(), nil
}
