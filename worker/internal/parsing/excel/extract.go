package excel

import (
	"example.com/bot_worker/pkg/models"
	"fmt"
	"github.com/xuri/excelize/v2"
)

func extractMetadata(f *excelize.File, fileName string, samples int) (*models.ExcelMetadata, error) {
	sheets := f.GetSheetList()
	if len(sheets) == 0 {
		return nil, fmt.Errorf("файл не содержит листов")
	}

	sheetsInfo := make([]models.SheetInfo, 0)

	for _, sheetName := range sheets {
		rows, err := f.GetRows(sheetName)
		if err != nil {
			continue
		}

		if len(rows) < 2 {
			continue
		}

		headers := rows[0]

		sampleRows := make([]map[string]interface{}, 0)

		maxSamples := samples
		if samples < 0 || samples > len(rows) {
			return nil, fmt.Errorf("samples err")
		}
		if samples == 0 {
			maxSamples = len(rows)
		}

		for i := 1; i < len(rows) && i <= maxSamples; i++ {
			rowMap := make(map[string]interface{})
			for j, header := range headers {
				if j < len(rows[i]) {
					rowMap["|"+header] = rows[i][j]
				} else {
					rowMap["|"+header] = ""
				}
			}
			sampleRows = append(sampleRows, rowMap)
		}

		sheetsInfo = append(sheetsInfo, models.SheetInfo{
			Name:       sheetName,
			RowCount:   len(rows) - 1,
			Columns:    headers,
			SampleRows: sampleRows,
		})
	}

	return &models.ExcelMetadata{
		Sheets:      sheetsInfo,
		ActiveSheet: sheets[0],
		FileName:    fileName,
	}, nil
}
