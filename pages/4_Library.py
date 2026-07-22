import streamlit as st
import os
import json

st.set_page_config(page_title="Library | RegWatch", page_icon="📚", layout="wide")

def main():
    st.title("📚 Legal Cards Library")
    st.markdown("Search, view, and manage your saved product compliance cards.")

    # ==========================================
    # DIRECTORY SETUP
    # ==========================================
    cards_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'legal_cards')
    os.makedirs(cards_dir, exist_ok=True)

    # Fetch all JSON files
    saved_files = [f for f in os.listdir(cards_dir) if f.endswith('.json')]

    if not saved_files:
        st.info("📭 Your library is empty. Go to the Editor to create and save your first Legal Card.")
        return

    # ==========================================
    # SEARCH ENGINE
    # ==========================================
    st.markdown("### 🔍 Search Engine")
    search_query = st.text_input("Search by keyword (Perimeter, Category, Market...)", "")
    
    # Load all cards into memory
    cards_data = []
    for file in saved_files:
        file_path = os.path.join(cards_dir, file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['_filename'] = file 
                cards_data.append(data)
        except Exception as e:
            st.error(f"Error reading {file}: {e}")

    # Apply search filter
    filtered_cards = []
    for card in cards_data:
        meta = card.get("metadata", {})
        # Create a combined string of metadata for easy searching
        searchable_text = f"{meta.get('perimeter', '')} {meta.get('category', '')} {meta.get('sub_category', '')} {meta.get('market', '')}".lower()
        
        if search_query.lower() in searchable_text:
            filtered_cards.append(card)

    # ==========================================
    # DISPLAY RESULTS
    # ==========================================
    st.markdown(f"**Found {len(filtered_cards)} Legal Card(s)**")
    
    for card in filtered_cards:
        meta = card.get("metadata", {})
        title = f"{meta.get('category', 'Unknown')} - {meta.get('market', 'Unknown')}"
        
        # Use expanders to keep the list clean
        with st.expander(f"📄 {title} | {meta.get('perimeter', '')}", expanded=False):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Sub-Category:** {meta.get('sub_category', 'N/A')}")
                st.markdown(f"**Last Updated:** {meta.get('last_updated', 'N/A')}")
                st.markdown(f"**Owner:** {meta.get('owner', 'N/A')}")
                
            with col2:
                # Prepare direct download from the library
                json_string = json.dumps(card, indent=4, ensure_ascii=False)
                st.download_button(
                    label="⬇️ Download JSON",
                    data=json_string,
                    file_name=card['_filename'],
                    mime="application/json",
                    key=f"dl_{card['_filename']}",
                    use_container_width=True
                )
                
                # Placeholder for future editing connection
                st.button("✏️ Load in Editor", key=f"edit_{card['_filename']}", disabled=True, help="Feature coming soon: Load this JSON back into the Editor page.")

            st.divider()
            
            # Display the raw JSON cleanly
            st.markdown("#### Card Content (JSON)")
            
            # Remove the internal filename key before displaying
            display_card = card.copy()
            display_card.pop('_filename', None)
            
            st.json(display_card)

if __name__ == "__main__":
    main()
