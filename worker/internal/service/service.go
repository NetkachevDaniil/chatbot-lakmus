package service

import (
	"github.com/xuri/excelize/v2"
)

type Analyzer interface {
	Name() string
	Analyze(f *excelize.File, sheetName string, params map[string]interface{}) (map[string]interface{}, error)
	RequiredColumns() []string
	ValidateParams(params map[string]interface{}) error
}
