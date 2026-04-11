-- Фикстура для плодовых деревьев с правильными категориями
-- Яблони (category_id=1), Сливы (category_id=2), Груши (category_id=3), Вишни (category_id=4)

-- Черешня Ипуть
INSERT INTO catalog_product (name, slug, description, care_tips, price, old_price, sku, unit, rating, rating_count, image, cart_image, category_id, tags, is_active, is_featured, stock, created_at, updated_at)
VALUES ('Черешня Ипуть', 'chereshnya-iput-new', 'Раннеспелый сорт черешни с крупными тёмно-бордовыми ягодами. Мякоть плотная, сладкая, сочная.', 'Посадка: солнечное место.\nПолив: регулярный.\nОбрезка: формирующая.', '1200.00', NULL, 'CHR-001', 'шт', '0.00', 0, '', '', 4, '', 1, 0, 30, '2026-01-01 00:36:00', '2026-01-01 00:36:00');
