package excel

import (
	"bytes"
	"example.com/bot_worker/pkg/models"
	"fmt"
	"github.com/xuri/excelize/v2"
)

func ReadDataFromBytes(data []byte, fileName string, samples int) (*models.ExcelMetadata, error) {
	f, err := excelize.OpenReader(bytes.NewReader(data))
	if err != nil {
		return nil, err
	}
	defer func() { _ = f.Close() }()

	return extractMetadata(f, fileName, samples)
}

func GetSheetDataFromBytes(data []byte, sheetName string) (*excelize.File, [][]string, error) {
	f, err := excelize.OpenReader(bytes.NewReader(data))
	if err != nil {
		return nil, nil, err
	}

	rows, err := f.GetRows(sheetName)
	if err != nil {
		defer func() { _ = f.Close() }()
		return nil, nil, err
	}

	if len(rows) < 2 {
		defer func() { _ = f.Close() }()
		return nil, nil, fmt.Errorf("лист '%s' не содержит данных", sheetName)
	}

	return f, rows, nil
}
