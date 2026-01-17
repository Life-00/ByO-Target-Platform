import React, { useState, useRef, useCallback, useMemo, memo } from 'react';
import {
  Book, FileText, FileBarChart, Search, Plus, Trash2, Settings, LogOut,
  CheckSquare, Square,
} from 'lucide-react';
import LibraryHeader from './LibraryHeader';
import LibraryTabs from './LibraryTabs';
import SearchBar from './SearchBar';
import LibraryList from './LibraryList';
import LibraryFooter from './LibraryFooter';

const LibraryPanel = ({
  papers,
  reports,
  selectedPaper,
  onSelectPaper,
  isOpen,
  toggleLibrary,
  checkedItems,
  onToggleCheck,
  onDeleteItem,
  onBatchSelect,
  onBatchDelete,
  onFileUpload,
  onLogout,
  onSettings,
  activeTab,
  onTabChange,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const fileInputRef = useRef(null);

  // Decide which list to display based on activeTab
  let currentList = [];
  if (activeTab === "papers") currentList = papers;
  else if (activeTab === "reports") currentList = reports;

  const filteredItems = currentList.filter(item =>
    item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.authors.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const areAllSelected = filteredItems.length > 0 && filteredItems.every(item => checkedItems.has(item.id));

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      onFileUpload(file);
    }
  };

  return (
    <div className={`
      ${isOpen ? 'w-80' : 'w-0'}
      transition-all duration-300 ease-in-out
      flex flex-col bg-white border-r border-gray-200 h-full overflow-hidden flex-shrink-0 relative
    `}>
      {/* Header */}
      <LibraryHeader />

      {/* Tabs */}
      <LibraryTabs activeTab={activeTab} onTabChange={onTabChange} />

      {/* Sub Header with Actions */}
      <div className="px-4 py-2 border-b border-gray-100 flex justify-between items-center bg-gray-50/50 shrink-0 h-10">
        <div className="flex items-center gap-3">
          <div
            className="cursor-pointer text-gray-400 hover:text-teal-600 transition-colors flex items-center"
            onClick={() => {
              const ids = filteredItems.map(i => i.id);
              onBatchSelect(ids, !areAllSelected);
            }}
            title={areAllSelected ? "전체 해제" : "전체 선택"}
          >
            {areAllSelected ? (
              <CheckSquare size={16} className="text-teal-600 fill-teal-50" />
            ) : (
              <Square size={16} />
            )}
          </div>

          {checkedItems.size > 0 && (
            <div className="h-4 w-px bg-gray-300 mx-1"></div>
          )}
          {checkedItems.size > 0 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (window.confirm(`${checkedItems.size}개의 항목을 삭제하시겠습니까?`)) {
                  onBatchDelete();
                }
              }}
              className="text-gray-400 hover:text-red-500 transition-colors flex items-center"
              title="선택된 항목 일괄 삭제"
            >
              <Trash2 size={15} />
            </button>
          )}

          {checkedItems.size === 0 && (
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-default">
              {activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}
            </h2>
          )}
        </div>

        {activeTab === 'papers' && (
          <div className="flex items-center">
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              accept=".pdf"
              onChange={handleFileChange}
            />
            <button
              onClick={handleUploadClick}
              className="p-1 text-teal-600 hover:bg-teal-100 rounded transition-colors flex items-center gap-1 text-[10px] font-bold"
              title="파일 업로드"
            >
              <Plus size={14} />
              <span>Upload</span>
            </button>
          </div>
        )}

        {activeTab !== 'papers' && (
          <span className="text-[10px] bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded font-mono">
            {currentList.length}
          </span>
        )}
      </div>

      {/* Search */}
      <SearchBar searchTerm={searchTerm} onSearchChange={setSearchTerm} />

      {/* List */}
      <LibraryList
        items={filteredItems}
        selectedPaper={selectedPaper}
        checkedItems={checkedItems}
        onSelectPaper={onSelectPaper}
        onToggleCheck={onToggleCheck}
        onDeleteItem={onDeleteItem}
      />

      {/* Footer */}
      <LibraryFooter onSettings={onSettings} onLogout={onLogout} />
    </div>
  );
};
export default memo(LibraryPanel);
