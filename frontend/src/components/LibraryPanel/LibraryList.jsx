import React, { useMemo } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Trash2, CheckSquare, Square, FileBarChart } from 'lucide-react';

const LibraryListItem = React.memo(({
  item,
  isChecked,
  isSelected,
  onToggleCheck,
  onSelectPaper,
  onDeleteItem,
}) => (
  <div
    className={`
      flex items-start gap-2 p-2 rounded-lg transition-all border border-transparent mb-1 group relative
      ${isSelected
        ? 'bg-teal-50 border-teal-200 shadow-sm'
        : 'hover:bg-gray-50 hover:border-gray-200'}
    `}
  >
    <div
      className="mt-1 cursor-pointer p-1 text-gray-400 hover:text-teal-700 transition-colors"
      onClick={(e) => {
        e.stopPropagation();
        onToggleCheck(item.id);
      }}
    >
      {isChecked ? (
        <CheckSquare size={16} className="text-teal-700 fill-teal-50" />
      ) : (
        <Square size={16} />
      )}
    </div>

    <div
      className="flex-1 cursor-pointer min-w-0"
      onClick={() => onSelectPaper(item)}
    >
      <div className="flex items-start gap-2 mb-1">
        {item.type === 'report' && <FileBarChart size={14} className="mt-0.5 text-indigo-500 flex-shrink-0" />}
        <h3 className={`font-semibold text-sm leading-tight truncate pr-4 ${isSelected ? 'text-teal-700' : 'text-gray-800'}`}>
          {item.title}
        </h3>
      </div>
      <div className="flex justify-between items-center text-xs text-gray-500 mt-2">
        <span className="truncate max-w-[120px]">
          {item.type === 'paper' ? item.authors.split(',')[0] + ' et al.' : item.authors}
        </span>
        <span className="bg-gray-200 px-1.5 py-0.5 rounded text-[10px] font-mono">{item.year}</span>
      </div>
    </div>

    <button
      onClick={(e) => {
        e.stopPropagation();
        if (window.confirm('정말 삭제하시겠습니까?')) {
          onDeleteItem(item.id, item.type);
        }
      }}
      className="absolute right-2 top-2 p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded opacity-0 group-hover:opacity-100 transition-all"
      title="삭제"
    >
      <Trash2 size={14} />
    </button>
  </div>
));

LibraryListItem.displayName = 'LibraryListItem';

const LibraryList = ({
  items,
  selectedPaper,
  checkedItems,
  onSelectPaper,
  onToggleCheck,
  onDeleteItem,
}) => {
  // Memoize items to prevent unnecessary re-renders
  const memoizedItems = useMemo(() => items, [items]);

  // Setup virtualizer
  const parentRef = React.useRef(null);
  const virtualizer = useVirtualizer({
    count: memoizedItems.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 88, // Estimated height of each item
    overscan: 10, // Render items outside viewport
  });

  const virtualItems = virtualizer.getVirtualItems();
  const totalSize = virtualizer.getTotalSize();

  if (memoizedItems.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
        <div className="flex flex-col items-center justify-center h-40 text-gray-400 text-xs gap-2">
          <div className="text-2xl">📭</div>
          <p>검색 결과가 없습니다.</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={parentRef}
      className="flex-1 overflow-y-auto custom-scrollbar"
      style={{ height: '100%' }}
    >
      <div
        style={{
          height: `${totalSize}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualItems.map((virtualItem) => {
          const item = memoizedItems[virtualItem.index];
          const isChecked = checkedItems.has(item.id);
          const isSelected = selectedPaper?.id === item.id;

          return (
            <div
              key={item.id}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              <LibraryListItem
                item={item}
                isChecked={isChecked}
                isSelected={isSelected}
                onToggleCheck={onToggleCheck}
                onSelectPaper={onSelectPaper}
                onDeleteItem={onDeleteItem}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default LibraryList;
