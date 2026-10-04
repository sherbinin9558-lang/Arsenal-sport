"""Catalog UI: paginated, search-first product management for large catalogs."""

import math


def render_catalog(
    *,
    categories,
    category_emoji,
    data_load_page,
    update_product,
    delete_product,
    bulk_import_products,
    data_conflict_error,
    can_write,
    page_size=50,
):
    st = __import__("streamlit")
    st.markdown(
        '<div class="section-kicker">PRODUCT LIBRARY</div>'
        '<div class="section-title">Каталог</div>'
        '<div class="section-subtitle">Поиск и редактирование работают постранично — приложение не рисует 10 000 товаров одновременно.</div>',
        unsafe_allow_html=True,
    )
    st.info("➕ Для нового товара откройте раздел «＋ Товар».")

    st.markdown("### 📥 Массовая загрузка товаров")
    st.caption("CSV/XLSX импортируется пакетно. Существующие товары можно обновлять по артикулу.")
    bulk_file = st.file_uploader(
        "Файл с товарами",
        type=["csv", "xlsx"],
        key="bulk_products_file",
    )
    bulk_update = st.checkbox(
        "Обновлять существующие товары по артикулу",
        value=False,
        key="bulk_update_existing",
    )
    if can_write and bulk_file and st.button("📦 Импортировать товары", type="primary", key="bulk_import_btn"):
        try:
            added, updated, skipped, errors = bulk_import_products(bulk_file, bulk_update)
            st.success(f"Готово: добавлено {added}, обновлено {updated}, пропущено {skipped}.")
            if errors:
        product_expander = st.expander(
            f"{category_emoji.get(p.get('category',''),'📦')} "
            f"{p.get('brand','')} {p.get('name','')} — {p.get('article','')}",
            key=f"catalog_expander_{key_suffix}",
            on_change="rerun",
        )
        if product_expander.open:
            with product_expander:
                edit = st.toggle("✏️ Редактировать", key=f"edit_{key_suffix}") if can_write else False
                if edit:
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        nn = st.text_input("Название", p.get("name",""), key=f"n_{key_suffix}")
                        nb = st.text_input("Бренд", p.get("brand",""), key=f"b_{key_suffix}")
                        na = st.text_input("Артикул", p.get("article",""), key=f"a_{key_suffix}")
                    with ec2:
                        ns = st.text_input("Размеры", p.get("sizes",""), key=f"s_{key_suffix}")
                        nc = st.text_input("Цвет", p.get("color",""), key=f"c_{key_suffix}")
                        ncat = st.selectbox(
                            "Категория",
                            categories,
                            index=categories.index(p.get("category","Другое")) if p.get("category","Другое") in categories else len(categories)-1,
                            key=f"ct_{key_suffix}",
                        )
                    nd = st.text_area("Описание", p.get("description",""), key=f"d_{key_suffix}")
                    nsp = st.text_input("Характеристики", p.get("specs",""), key=f"sp_{key_suffix}")
                    new_original = st.file_uploader(
                        "📷 Исходное фото товара",
                        type=["jpg", "jpeg", "png", "webp"],
                        key=f"orig_{key_suffix}",
                    )
                    if st.button("💾 Сохранить", key=f"save_{key_suffix}"):
                        updated = {
                            "name": nn, "brand": nb, "article": na, "sizes": ns,
                            "color": nc, "description": nd, "specs": nsp,
                            "category": ncat, "date_added": p.get("date_added", ""),
                            "price": p.get("price", ""),
                            "stock": p.get("stock", 0),
                            "total_stock": p.get("total_stock", p.get("stock", 0)),
                            "stock_by_size": p.get("stock_by_size", {}),
                        }
                        if p.get("card_image"):
                            updated["card_image"] = p["card_image"]
                        if p.get("original_image"):
                            updated["original_image"] = p["original_image"]
                        if new_original:
                            import base64, io
                            from PIL import Image
                            original_buf = io.BytesIO()
                            Image.open(new_original).convert("RGB").save(original_buf, format="JPEG", quality=95)
                            updated["original_image"] = base64.b64encode(original_buf.getvalue()).decode("ascii")
                        try:
                            update_product(record_id, updated, existing=p)
                            st.success("Обновлено.")
                            st.rerun()
                        except data_conflict_error as e:
                            st.warning(str(e))
                        except Exception as e:
                            st.error(f"Не удалось сохранить товар: {e}")
                else:
                    st.write(f"**Размеры:** {p.get('sizes','—')}")
                    st.write(f"**Цвет:** {p.get('color','—')}")
                    st.write(f"**Описание:** {p.get('description','—')}")
                    st.write(f"**Характеристики:** {p.get('specs','—')}")
                    st.caption(f"Добавлено: {p.get('date_added','—')}")

                if can_write and st.button("🗑️ Удалить", key=f"del_{key_suffix}"):
                    try:
                        delete_product(record_id, existing=p)
                        st.rerun()
                    except data_conflict_error as e:
                        st.warning(str(e))
                    except Exception as e:
                        st.error(f"Не удалось удалить товар: {e}")
